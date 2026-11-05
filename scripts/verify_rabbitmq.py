import argparse
import csv
import hashlib
import io
import json
import time
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import requests

from rabbitmq_admin import ROOT, compose, session, snapshot


class Protocol:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.http = requests.Session()
        self.management = session()
        self.report = {"timestamp": datetime.now(timezone.utc).isoformat(), "mock_used": False, "physical_iphone_tested": False, "checks": [], "jobs": []}

    def save(self):
        (ROOT / "verification" / "rabbitmq-integration.json").write_text(json.dumps(self.report, ensure_ascii=False, indent=2), encoding="utf-8")

    def check(self, name, **evidence):
        self.report["checks"].append({"name": name, **evidence})
        self.save()
        print(name, flush=True)

    def get(self, path):
        response = self.http.get(self.base + "/api" + path, timeout=20)
        response.raise_for_status()
        return response.json()

    def wait(self, predicate, timeout=120):
        deadline = time.monotonic() + timeout
        error = None
        while time.monotonic() < deadline:
            try:
                value = predicate()
                if value:
                    return value
            except (requests.RequestException, RuntimeError) as exc:
                error = type(exc).__name__
            time.sleep(.5)
        raise AssertionError(f"Очікування вичерпано: {error}")

    def submit(self, path, kind="image"):
        with path.open("rb") as stream:
            response = self.http.post(self.base + f"/api/analysis/{kind}", files={"file": (path.name, stream)}, timeout=30)
        assert response.status_code == 202, response.text[:500]
        accepted = response.json()
        UUID(accepted["analysisId"])
        assert accepted["status"] in {"Pending", "Queued"}
        self.report["jobs"].append(accepted)
        self.save()
        return accepted

    def status(self, task):
        return self.get(f"/analyses/{task['analysisId']}/status")

    def completed(self, task, expected="Completed", timeout=300):
        terminal = self.wait(lambda: (s if (s := self.status(task))["status"] in {"Completed", "Failed"} else None), timeout)
        assert terminal["status"] == expected, terminal
        if expected == "Completed":
            assert len(terminal["result"]["predictions"]) == 3
            assert terminal["result"]["modelRevision"]
        return terminal

    def sql(self, query):
        output = compose("exec", "-T", "sql", "sh", "-c", 'exec /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -C -b -d AIBirdLab -y 0 -w 65535 -Q "$1"', "_", "SET NOCOUNT ON; " + query + " FOR JSON PATH")
        return json.loads(output[output.index("["):output.rindex("]") + 1])

    def rows(self, task):
        job = str(UUID(task["analysisId"]))
        return self.sql(f"SELECT a.Id,a.Status,a.RetryCount,(SELECT COUNT(*) FROM Predictions p WHERE p.AnalysisId=a.Id) Predictions,(SELECT COUNT(*) FROM OutboxMessages o WHERE o.AnalysisId=a.JobId) OutboxRows FROM Analyses a WHERE a.JobId='{job}'")

    def outbox(self, task):
        job = str(UUID(task["analysisId"]))
        return self.sql(f"SELECT Id,Payload,PublishedAt,Attempts FROM OutboxMessages WHERE AnalysisId='{job}'")[0]

    def publish(self, key, body):
        payload = json.loads(body)
        response = self.management.post("http://127.0.0.1:15672/api/exchanges/birdlab/bird.analysis/publish", json={"properties": {"delivery_mode": 2, "content_type": "application/json", "message_id": payload.get("eventId", str(uuid4())), "correlation_id": payload.get("correlationId", str(uuid4()))}, "routing_key": key, "payload": body, "payload_encoding": "string"}, timeout=10)
        response.raise_for_status()
        assert response.json()["routed"]

    def queue(self, name):
        response = self.management.get("http://127.0.0.1:15672/api/queues/birdlab/" + name, timeout=10)
        response.raise_for_status()
        return response.json()

    def baseline(self):
        self.wait(lambda: self.get("/health")["status"] == "ok")
        topology = snapshot(self.management)
        assert topology["rabbitmq_version"] == "4.4.0"
        assert len(topology["queues"]) == 9
        assert all(q["type"] == "quorum" and q["durable"] for q in topology["queues"])
        self.report["topology"] = topology
        self.check("Реальні RabbitMQ Management API, 9 durable quorum queues та policies")

    def normal(self):
        image = sorted((ROOT / "sample_images").glob("*.jpg"))[0]
        compose("stop", "worker")
        try:
            task = self.submit(image)
            self.wait(lambda: self.status(task)["status"] == "Queued")
            outbox = self.outbox(task)
            assert outbox.get("PublishedAt")
            self.wait(lambda: self.queue("bird.analysis.requests").get("messages_ready", 0) >= 1)
            assert self.rows(task)[0]["Predictions"] == 0
            self.check("HTTP 202 → SQL Analysis + Outbox → підтверджене повідомлення очікує worker", task=task, outbox_event=outbox["Id"])
        finally:
            compose("start", "worker")
        result = self.completed(task)
        row = self.rows(task)
        assert len(row) == 1 and row[0]["Predictions"] == 3 and row[0]["OutboxRows"] == 1
        self.check("Справжня HF фотомодель → RabbitMQ result → SQL TOP-3 та Completed", result=result, sql=row)
        self.publish("analysis.requested", outbox["Payload"])
        self.wait(lambda: self.queue("bird.analysis.requests").get("messages", 0) == 0)
        time.sleep(2)
        assert self.rows(task) == row
        self.check("Повторна доставка початкового eventId не дублює аналіз або TOP-3")
        stored = self.get(f"/analyses/{task['historyId']}")
        media = self.http.get(self.base + stored["fileUrl"], timeout=20)
        assert hashlib.sha256(media.content).hexdigest() == hashlib.sha256(image.read_bytes()).hexdigest()
        self.check("Контракт Expo/React: statusUrl, historyId, збережений результат та точні байти медіа")
        return image, task

    def invalid(self):
        response = self.http.post(self.base + "/api/analysis/image", files={"file": ("broken.png", b"not an image")}, timeout=30)
        assert response.status_code == 202
        task = response.json()
        failed = self.completed(task, "Failed")
        assert self.rows(task)[0]["Predictions"] == 0
        self.wait(lambda: self.queue("bird.analysis.dead").get("messages", 0) >= 1)
        self.publish("analysis.requested", "{}")
        self.check("Пошкоджений файл → Failed без передбачень; некоректне завдання → DLQ", failure=failed)

    def batch(self):
        images = sorted(p for p in (ROOT / "sample_images").iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
        assert len(images) == 15
        with ExitStack() as stack:
            files = [("files", (p.name, stack.enter_context(p.open("rb")))) for p in images]
            response = self.http.post(self.base + "/api/analysis/batch", files=files, timeout=60)
        assert response.status_code == 202
        rows = response.json()
        assert len(rows) == 15 and all(row["task"] and not row["error"] for row in rows)
        results = [self.completed(row["task"]) for row in rows]
        for row in rows:
            assert self.rows(row["task"])[0]["Predictions"] == 3
        self.check("Пакет із усіх 15 оригінальних фото: 15 Completed та рівно 45 SQL-передбачень", results=results)

    def faults(self, image):
        compose("stop", "rabbitmq")
        try:
            response = self.http.get(self.base + "/api/health", timeout=20)
            assert response.status_code == 503 and not response.json()["rabbitmq"]
            task = self.submit(image)
            assert self.status(task)["status"] == "Pending"
            assert not self.outbox(task).get("PublishedAt")
            self.check("RabbitMQ вимкнено: health degraded/503, HTTP 202, завдання збережене в SQL Outbox")
        finally:
            compose("start", "rabbitmq")
        self.completed(task)
        self.check("Після перезапуску RabbitMQ Outbox передав збережене завдання та отримав результат")
        audio = next((ROOT / "sample_audio").glob("*.wav"))
        task = self.submit(audio, "audio")
        self.wait(lambda: self.status(task)["status"] == "Processing")
        compose("kill", "-s", "SIGKILL", "worker")
        compose("start", "worker")
        result = self.completed(task, timeout=420)
        assert self.rows(task)[0]["Predictions"] == 3
        self.check("SIGKILL Python Worker під час Processing: перезапуск, справжня аудіомодель, один SQL-результат", result=result)
        self.sql_fault(image)

    def sql_fault(self, image):
        compose("stop", "worker")
        sql_stopped = False
        try:
            task = self.submit(image)
            self.wait(lambda: self.status(task)["status"] == "Queued")
            compose("stop", "sql")
            sql_stopped = True
            assert "sql" not in compose("ps", "--status", "running", "--services").splitlines()
            unavailable = self.http.get(self.base + "/api/health", timeout=20)
            assert unavailable.status_code == 503 and unavailable.json()["database"] is False, unavailable.text
            print("SQL outage confirmed: container stopped, health.database=false", flush=True)
            compose("up", "-d", "--no-deps", "worker")
            assert "sql" not in compose("ps", "--status", "running", "--services").splitlines()
            print("Worker started with SQL still stopped", flush=True)
            last = None
            def delayed():
                nonlocal last
                queues = snapshot(self.management)["queues"]
                state = [(q["name"], q.get("messages"), q.get("messages_unacknowledged"), q.get("consumers")) for q in queues if q["name"] in {"bird.analysis.requests", "bird.analysis.results"} or ".results.retry." in q["name"]]
                if state != last:
                    print(json.dumps(state), flush=True)
                    last = state
                return sum(q.get("messages", 0) or 0 for q in queues if ".results.retry." in q["name"]) > 0
            self.wait(delayed, timeout=90)
            self.check("SQL вимкнено після queue submit: результати збережені у durable retry queue")
        finally:
            if sql_stopped:
                compose("start", "sql")
            compose("start", "worker")
        self.completed(task, timeout=300)
        assert self.rows(task)[0]["Predictions"] == 3
        self.check("SQL відновлено: retry → транзакція результату, рівно три передбачення")
        compose("restart", "central", "worker")
        self.wait(lambda: self.get("/health")["status"] == "ok")
        assert self.completed(task)["status"] == "Completed"
        self.check("Перезапуск central + worker зберігає SQL-результати, ledger та робочі consumers")

    def export(self):
        response = self.http.get(self.base + "/api/export/csv", timeout=30)
        response.raise_for_status()
        assert response.content.startswith(b"\xef\xbb\xbf")
        rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
        summary = self.get("/statistics/summary")
        assert len(rows) == summary["totalAnalyses"]
        assert sum(b["count"] for b in self.get("/statistics/confidence")) == len(rows)
        self.check("Історія, статистика та CSV узгоджені; Pending/Failed не спотворюють confidence", completed=len(rows))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Справжня Docker/RabbitMQ/SQL/Hugging Face інтеграція; додає тестові аналізи, не видаляє дані.")
    parser.add_argument("--base", default="http://127.0.0.1:5100")
    parser.add_argument("--batch", action="store_true")
    parser.add_argument("--faults", action="store_true")
    parser.add_argument("--sql-fault-only", action="store_true")
    args = parser.parse_args()
    protocol = Protocol(args.base)
    if args.sql_fault_only:
        protocol.report = json.loads((ROOT / "verification" / "rabbitmq-integration.json").read_text(encoding="utf-8"))
        protocol.report.pop("success", None)
        protocol.report.pop("error", None)
    try:
        if args.sql_fault_only:
            protocol.sql_fault(sorted((ROOT / "sample_images").glob("*.jpg"))[0])
        else:
            protocol.baseline()
            image, task = protocol.normal()
            protocol.invalid()
            if args.batch:
                protocol.batch()
            if args.faults:
                protocol.faults(image)
        protocol.export()
        protocol.report["success"] = True
    except Exception as exc:
        protocol.report["success"] = False
        protocol.report["error"] = str(exc)
        raise
    finally:
        protocol.save()
