import argparse
import copy
import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import requests

from local_blockchain import Anvil, ROOT
from subscription_data import sql


class Protocol:
    def __init__(self, args):
        self.args = args
        self.artifacts = ROOT / ".test-artifacts/subscriptions"
        self.artifacts.mkdir(parents=True, exist_ok=True)
        self.anvil = Anvil(args.rpc)
        self.base = f"http://127.0.0.1:{args.port}/api"
        self.http = requests.Session()
        self.processes = []
        self.logs = []
        self.env = os.environ.copy()
        for line in (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                name, value = line.split("=", 1)
                self.env[name.strip()] = value.strip().strip("\"'")
        self.database = "BirdLabSubscriptionIntegration_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.report = {"startedAt": datetime.now(timezone.utc).isoformat(), "mock_used": False, "network": "Local Anvil", "chainId": 31337, "database": self.database, "baseSepoliaPaymentTested": False, "physicalIphoneTested": False, "realWalletExtensionTested": False, "aiTestRequested": not args.skip_ai, "checks": []}
        self.report["execution"] = "Docker Compose" if args.docker else "Host services with Docker RabbitMQ"
        self.broker_url = "http://127.0.0.1:15673" if args.docker else "http://127.0.0.1:15672"
        self.docker_started = False
        self.docker_project = "birds-subscription-check-" + uuid4().hex[:8]
        if args.docker:
            self.report["composeProject"] = self.docker_project

    def record(self, name, **data):
        self.report["checks"].append({"name": name, **data})
        self.save()
        print(name, flush=True)

    def save(self):
        name = "subscriptions-docker.json" if self.args.docker else "subscriptions-integration.json"
        (ROOT / "verification" / name).write_text(json.dumps(self.report, ensure_ascii=False, indent=2), encoding="utf-8")

    def compose(self, *args, timeout=300):
        command = ["docker", "compose", "-p", self.docker_project, "-f", "compose.yaml", "-f", "compose.subscriptions-test.yaml", "--profile", "blockchain-local", *args]
        result = subprocess.run(command, cwd=ROOT, env=self.env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        if result.returncode:
            output = result.stdout + result.stderr
            for name, value in self.env.items():
                if value and any(marker in name.upper() for marker in ("PASSWORD", "KEY", "TOKEN")):
                    output = output.replace(value, "[REDACTED]")
            raise RuntimeError(output[-5000:])
        return result.stdout

    def sql(self, query):
        if not self.args.docker:
            return sql(query, self.database)
        output = self.compose("exec", "-T", "sql", "sh", "-c", 'exec /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -C -b -y 0 -w 65535 -d "$1" -Q "$2"', "birdlab-test", self.database, "SET NOCOUNT ON; " + query)
        output = "".join(output.splitlines()).strip()
        start = output.find("[")
        return json.loads(output[start:output.rfind("]") + 1]) if start >= 0 else []

    def start(self, name, command, env=None, cwd=ROOT):
        log = (self.artifacts / f"{name}.log").open("w", encoding="utf-8")
        self.logs.append(log)
        process = subprocess.Popen(command, cwd=cwd, env=env or self.env, stdout=log, stderr=subprocess.STDOUT)
        self.processes.append(process)
        return process

    @staticmethod
    def wait(predicate, seconds=60):
        deadline = time.monotonic() + seconds
        last = None
        while time.monotonic() < deadline:
            try:
                value = predicate()
                if value:
                    return value
            except (requests.RequestException, RuntimeError) as error:
                last = type(error).__name__
            time.sleep(.4)
        raise RuntimeError(f"Timed out waiting for a real service: {last}")

    def request(self, method, path, expected=200, **kwargs):
        response = self.http.request(method, self.base + path, timeout=60, **kwargs)
        if response.status_code != expected:
            raise RuntimeError(f"{method} {path} returned HTTP {response.status_code}, expected {expected}.")
        return response.json() if response.content else None

    def configure(self):
        if self.args.docker:
            return self.configure_docker()
        try:
            self.anvil.require_local()
        except requests.RequestException:
            self.start("anvil", ["anvil", "--host", "127.0.0.1", "--port", str(int(self.args.rpc.rsplit(":", 1)[1])), "--chain-id", "31337", "--silent"])
            self.wait(lambda: self.anvil.rpc("eth_chainId"))
        self.deployment = self.anvil.deploy()
        self.report["deployment"] = self.deployment
        self.owner, self.payer = self.anvil.rpc("eth_accounts")[:2]
        sql_server = self.env.get("BIRDLAB_SQL_SERVER", r".\SQLEXPRESS")
        self.env.update({"ASPNETCORE_ENVIRONMENT": "Development", "ASPNETCORE_URLS": f"http://127.0.0.1:{self.args.port}", "ConnectionStrings__BirdLab": f"Server={sql_server};Database={self.database};Trusted_Connection=True;TrustServerCertificate=True", "Blockchain__Enabled": "true", "Blockchain__AllowLocalAnvil": "true", "Blockchain__TestMode": "true", "Blockchain__ChainId": "31337", "Blockchain__RpcUrl": self.args.rpc, "Blockchain__PublicRpcUrl": self.args.rpc, "Blockchain__TokenAddress": self.deployment["tokenAddress"], "Blockchain__PaymentContractAddress": self.deployment["paymentContractAddress"], "Blockchain__Confirmations": "3", "Blockchain__PollSeconds": "2", "RabbitMQ__Password": self.env.get("RABBITMQ_PASSWORD", ""), "RabbitMQ__Username": self.env.get("RABBITMQ_USERNAME", "birdlab"), "AiServer__InternalKey": self.env.get("AI_INTERNAL_KEY", ""), "AiServer__BaseUrl": "http://127.0.0.1:8000", "BIRD_OFFLINE": "true"})
        if not self.args.skip_ai:
            self.configure_broker()
        self.env["Logging__LogLevel__Microsoft.EntityFrameworkCore.Database.Command"] = "Information"
        self.env["Logging__LogLevel__Microsoft.AspNetCore"] = "Information"
        binary = str(ROOT / "central-server/bin/Debug/net10.0/BirdLab.Api.dll")
        log = (self.artifacts / "migration.log").open("w", encoding="utf-8")
        self.logs.append(log)
        subprocess.run(["dotnet", binary, "--migrate-db"], cwd=ROOT / "central-server", env=self.env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)
        central = self.start("central", ["dotnet", binary], cwd=ROOT / "central-server")
        def listening():
            if central.poll() is not None:
                raise OSError("The owned ASP.NET process exited before listening. Check the port and central.log.")
            return f"Now listening on: http://127.0.0.1:{self.args.port}" in (self.artifacts / "central.log").read_text(encoding="utf-8", errors="replace")
        self.wait(listening)
        self.wait(lambda: requests.get(self.base + "/health/live", timeout=3).status_code == 200)
        network = self.request("GET", "/subscriptions/network")
        if network["paymentContractAddress"].lower() != self.deployment["paymentContractAddress"].lower():
            raise RuntimeError("Another server is listening on the selected port; no account was created.")
        if not self.args.skip_ai:
            self.env["BIRD_MEDIA_ROOT"] = str(ROOT / "central-server/storage")
            self.env["BIRD_WORKER_STATE"] = str(self.artifacts / "worker-state")
            self.start("worker", [str(ROOT / ".venv/Scripts/python.exe"), "-X", "utf8", "ai-server/worker.py"])
            self.start("ai", [str(ROOT / ".venv/Scripts/python.exe"), "-X", "utf8", "-m", "uvicorn", "ai_api.app:app", "--app-dir", "ai-server", "--host", "127.0.0.1", "--port", "8000"])
            self.wait(lambda: requests.get(self.base + "/health", timeout=12).status_code == 200, 120)
        self.record("Real Anvil contracts deployed; isolated SQL migrations applied", **self.deployment)

    def configure_docker(self):
        if self.args.skip_ai:
            raise ValueError("Docker verification requires the complete AI scenario.")
        if self.args.rpc != "http://127.0.0.1:8545":
            raise ValueError("Docker verification publishes Anvil on loopback port 8545 only.")
        self.env.update({"SUBSCRIPTION_TEST_DATABASE": self.database, "SUBSCRIPTION_TEST_PORT": str(self.args.port), "SUBSCRIPTION_TEST_VHOST": "birdlab", "SUBSCRIPTION_TEST_TOKEN": "", "SUBSCRIPTION_TEST_CONTRACT": ""})
        self.docker_started = True
        self.compose("up", "-d", "--no-build", "--wait", "--wait-timeout", "180", "sql", "rabbitmq", "ai", "anvil")
        cookie = self.compose("exec", "-T", "rabbitmq", "stat", "-c", "%U %a", "/var/lib/rabbitmq/.erlang.cookie").strip().split()
        assert len(cookie) == 2 and cookie[0] == "rabbitmq" and cookie[1] in {"400", "600"}
        self.report["rabbitmqCookiePermissions"] = {"owner": cookie[0], "mode": cookie[1], "valueRead": False}
        self.record("Isolated Docker SQL, RabbitMQ, AI and Anvil passed startup health checks")
        self.wait(lambda: self.anvil.rpc("eth_chainId"))
        self.deployment = self.anvil.deploy()
        self.report["deployment"] = self.deployment
        self.owner, self.payer = self.anvil.rpc("eth_accounts")[:2]
        self.configure_broker()
        self.env.update({"SUBSCRIPTION_TEST_TOKEN": self.deployment["tokenAddress"], "SUBSCRIPTION_TEST_CONTRACT": self.deployment["paymentContractAddress"], "SUBSCRIPTION_TEST_VHOST": self.report["rabbitmqVhost"]})
        self.compose("up", "-d", "--no-build", "migrate", "central", "worker")
        self.wait(lambda: requests.get(self.base + "/health", timeout=12).status_code == 200, 180)
        network = self.request("GET", "/subscriptions/network")
        assert network["paymentContractAddress"].lower() == self.deployment["paymentContractAddress"].lower()
        containers = [json.loads(line) for line in self.compose("ps", "--format", "json").splitlines() if line.strip()]
        self.report["containers"] = [{key: item.get(key) for key in ("ID", "Name", "Service", "Image", "State", "Health")} for item in containers]
        image_ids = subprocess.check_output(["docker", "inspect", "--format", "{{.Image}}", *[item["ID"] for item in containers]], cwd=ROOT, env=self.env, text=True, encoding="utf-8").splitlines()
        assert len(image_ids) == len(containers)
        for item, image_id in zip(self.report["containers"], image_ids):
            item["ImageId"] = image_id
        self.report["health"] = self.request("GET", "/health")
        self.record("Real Anvil contracts deployed; isolated SQL migrations applied", **self.deployment)

    def capture_evidence(self):
        self.report["sqlEvidence"] = {
            "analyses": self.sql(f"SELECT a.JobId,a.AnalysisType,a.Status,a.ModelName,a.ModelRevision,u.Status UsageStatus,(SELECT COUNT(*) FROM Predictions p WHERE p.AnalysisId=a.Id) Predictions,(SELECT COUNT(*) FROM OutboxMessages o WHERE o.AnalysisId=a.JobId AND o.PublishedAt IS NOT NULL) PublishedOutbox,(SELECT COUNT(*) FROM InboxMessages i WHERE i.AnalysisId=a.JobId) InboxEvents FROM Analyses a JOIN UsageRecords u ON u.JobId=a.JobId WHERE a.UserId='{self.user_id}' ORDER BY a.Id FOR JSON PATH"),
            "subscriptions": self.sql(f"SELECT PlanId,Status,AnalysisLimit,AnalysesUsed,StartDate,EndDate FROM UserSubscriptions WHERE UserId='{self.user_id}' ORDER BY CreatedAt FOR JSON PATH"),
            "payments": self.sql(f"SELECT ChainId,TransactionHash,BlockNumber,LogIndex,Amount,Status FROM CryptoPayments WHERE UserId='{self.user_id}' ORDER BY CreatedAt FOR JSON PATH")
        }
        if not self.args.skip_ai:
            rows = self.report["sqlEvidence"]["analyses"]
            assert len(rows) == 2 and all(row["Status"] == "Completed" and row["UsageStatus"] == "Consumed" and row["Predictions"] == 3 and row["PublishedOutbox"] == 1 and row["InboxEvents"] >= 1 for row in rows)
            broker = requests.Session()
            broker.auth = (self.env["RABBITMQ_USERNAME"], self.env["RABBITMQ_PASSWORD"])
            response = broker.get(self.broker_url + "/api/queues/" + self.report["rabbitmqVhost"], timeout=10)
            response.raise_for_status()
            self.report["rabbitmqEvidence"] = [{key: row.get(key) for key in ("name", "type", "durable", "messages_ready", "messages_unacknowledged", "consumers", "message_stats")} for row in response.json()]
            self.record("SQL Outbox, Inbox, TOP-3 results and consumed quota independently verified")

    def configure_broker(self):
        broker = requests.Session()
        broker.auth = (self.env["RABBITMQ_USERNAME"], self.env["RABBITMQ_PASSWORD"])
        self.wait(lambda: broker.get(self.broker_url + "/api/overview", timeout=5).status_code == 200, 90)
        vhost = "birdlab-subscriptions-" + uuid4().hex[:10]
        definitions = json.loads((ROOT / "rabbitmq/definitions.json").read_text())
        isolated = {"vhosts": [{"name": vhost}], "permissions": [{"user": self.env["RABBITMQ_USERNAME"], "vhost": vhost, "configure": ".*", "write": ".*", "read": ".*"}]}
        for name in ("exchanges", "queues", "bindings", "policies", "parameters"):
            if name in definitions:
                isolated[name] = [dict(copy.deepcopy(item), vhost=vhost) for item in definitions[name]]
        response = broker.post(self.broker_url + "/api/definitions", json=isolated, timeout=20)
        response.raise_for_status()
        self.env.update({"RabbitMQ__VirtualHost": vhost, "RABBITMQ_VHOST": vhost})
        self.report["rabbitmqVhost"] = vhost

    def account(self):
        session = self.request("POST", "/auth/register", 201, json={"email": f"integration-{uuid4().hex}@example.test", "password": "Bird!" + uuid4().hex + "9Aa", "useBearerToken": True})
        self.http.headers["Authorization"] = "Bearer " + session["accessToken"]
        self.user_id = session["user"]["id"]
        assert self.request("GET", "/subscriptions/me")["plan"] == "FREE"
        nonce = self.request("POST", "/wallets/nonce", json={"walletAddress": self.payer})
        signature = self.anvil.rpc("personal_sign", ["0x" + nonce["message"].encode().hex(), self.payer])
        self.request("POST", "/wallets/verify", json={"nonce": nonce["nonce"], "message": nonce["message"], "signature": signature})
        self.request("POST", "/wallets/verify", 400, json={"nonce": nonce["nonce"], "message": nonce["message"], "signature": signature})
        self.record("Identity registration, bearer session and real personal_sign SIWE; nonce replay rejected")

    def payment(self, plan=1, check_pending=True, test_reorg=False):
        order = self.request("POST", "/subscriptions/orders", 201, json={"planId": plan, "walletAddress": self.payer, "amount": 1})
        amount = 5_000_000 if plan == 1 else 10_000_000
        assert order["amount"] == str(amount)
        self.anvil.call(self.owner, self.deployment["tokenAddress"], "mint(address,uint256)", self.payer, amount)
        approval = self.anvil.call(self.payer, self.deployment["tokenAddress"], "approve(address,uint256)", self.deployment["paymentContractAddress"], amount)
        wrong = self.request("POST", "/subscriptions/payments/verify", json={"orderId": order["id"], "transactionHash": approval})
        assert wrong["status"] == "Rejected"
        snapshot = self.anvil.rpc("evm_snapshot")
        transaction = self.anvil.call(self.payer, self.deployment["paymentContractAddress"], "purchaseSubscription(bytes32,uint256)", order["orderId"], plan)
        receipt = self.anvil.receipt(transaction)
        assert any(log["address"].lower() == self.deployment["paymentContractAddress"].lower() for log in receipt["logs"])
        result = self.request("POST", "/subscriptions/payments/verify", json={"orderId": order["id"], "transactionHash": transaction})
        if check_pending:
            assert result["status"] == "Pending", result["status"]
            assert self.request("GET", "/subscriptions/me")["planId"] != plan
        self.anvil.rpc("anvil_mine", ["0x2"])
        result = self.request("POST", "/subscriptions/payments/verify", json={"orderId": order["id"], "transactionHash": transaction})
        assert result["status"] == "Confirmed", result["status"]
        period = self.request("GET", "/subscriptions/me")
        assert period["planId"] == plan
        for _ in range(2):
            self.request("POST", "/subscriptions/payments/verify", json={"orderId": order["id"], "transactionHash": transaction})
        assert self.request("GET", "/subscriptions/me")["endDate"] == period["endDate"]
        if test_reorg:
            orphaned_hash = result["transactionHash"]
            assert self.anvil.rpc("evm_revert", [snapshot])
            lost = self.request("POST", "/subscriptions/payments/verify", json={"orderId": order["id"], "transactionHash": transaction})
            assert lost["status"] == "Reorged"
            assert self.request("GET", "/subscriptions/me")["plan"] == "FREE"
            replay = self.anvil.call(self.payer, self.deployment["paymentContractAddress"], "purchaseSubscription(bytes32,uint256)", order["orderId"], plan)
            self.anvil.rpc("anvil_mine", ["0x2"])
            restored = self.request("POST", "/subscriptions/payments/verify", json={"orderId": order["id"], "transactionHash": replay})
            assert restored["status"] == "Confirmed"
            assert self.request("GET", "/subscriptions/me")["endDate"] == period["endDate"]
            result = restored
            self.record("Real Anvil reorg revoked access; canonical transaction restored same period without extension", orphanedTransactionHash=orphaned_hash, canonicalTransactionHash=restored["transactionHash"])
        rows = self.sql(f"SELECT Status,ChainId,TransactionHash,LogIndex,Amount FROM CryptoPayments WHERE PaymentOrderId='{order['id']}' FOR JSON PATH")
        assert len(rows) == 1 and rows[0]["Status"] == "Confirmed" and rows[0]["Amount"] == amount
        assert rows[0]["TransactionHash"].lower() == result["transactionHash"].lower()
        assert rows[0]["LogIndex"] == result["logIndex"]
        self.record(f"Plan {plan}: mint, exact approval, real contract event, confirmations, SQL activation and replay protection", orderId=order["orderId"], transactionHash=result["transactionHash"], blockNumber=result["blockNumber"], logIndex=result["logIndex"], amount=str(amount), remaining=period["remaining"])
        return order

    def analysis(self, path, kind):
        before = self.request("GET", "/subscriptions/usage")["remaining"]
        with path.open("rb") as stream:
            accepted = self.request("POST", f"/analysis/{kind}", 202, files={"file": (path.name, stream)})
        assert self.request("GET", "/subscriptions/usage")["remaining"] == before - 1
        def terminal():
            status = self.request("GET", f"/analyses/{accepted['analysisId']}/status")
            return status if status["status"] in {"Completed", "Failed"} else None
        status = self.wait(terminal, 300)
        assert status["status"] == "Completed", "Real AI analysis failed; inspect local worker log."
        assert len(status["result"]["predictions"]) == 3
        row = self.sql(f"SELECT a.Status,a.ModelName,a.ModelRevision,a.MetadataJson,u.Status UsageStatus FROM Analyses a JOIN UsageRecords u ON u.JobId=a.JobId WHERE a.JobId='{accepted['analysisId']}' FOR JSON PATH")[0]
        assert row["UsageStatus"] == "Consumed" and json.loads(row["MetadataJson"])["mock_used"] is False
        self.record(f"Real RabbitMQ -> Python Hugging Face -> SQL {kind} analysis; one quota unit consumed", analysisId=accepted["analysisId"], model=row["ModelName"], modelRevision=row.get("ModelRevision"), metadata=json.loads(row["MetadataJson"]), predictions=status["result"]["predictions"], mock_used=False, remaining=before - 1)

    def verify_free_limits_and_privacy(self):
        assert requests.get(self.base + "/subscriptions/me", timeout=10).status_code == 401
        other = requests.Session()
        response = other.post(self.base + "/auth/register", json={"email": f"free-integration-{uuid4().hex}@example.test", "password": "Bird!" + uuid4().hex + "9Aa", "useBearerToken": True}, timeout=30)
        assert response.status_code == 201
        session = response.json()
        other.headers["Authorization"] = "Bearer " + session["accessToken"]
        primary = self.sql(f"SELECT TOP (1) Id,JobId FROM Analyses WHERE UserId='{self.user_id}' ORDER BY Id FOR JSON PATH")[0]
        for path, expected in ((f"/analyses/{primary['JobId']}/status", 404), (f"/analyses/{primary['Id']}", 404), (f"/analyses/{primary['Id']}/file", 404), ("/analyses/gallery", 403), ("/statistics/species", 403), ("/statistics/evaluations", 403)):
            assert other.get(self.base + path, timeout=15).status_code == expected, path
        image = sorted((ROOT / "sample_images").glob("*.jpg"))[0]
        audio = sorted((ROOT / "sample_audio").glob("*.wav"))[0]
        with audio.open("rb") as stream:
            assert other.post(self.base + "/analysis/audio", files={"file": (audio.name, stream)}, timeout=30).status_code == 403
        with image.open("rb") as stream:
            assert other.post(self.base + "/analysis/batch", files={"files": (image.name, stream)}, timeout=30).status_code == 403
        assert other.get(self.base + "/subscriptions/usage", timeout=15).json()["remaining"] == 5
        self.record("Anonymous and foreign history/media denied; FREE audio, gallery, batch and advanced statistics denied without consuming quota")

        def submit(_):
            with image.open("rb") as stream:
                response = requests.post(self.base + "/analysis/image", headers=dict(other.headers), files={"file": (image.name, stream)}, timeout=60)
            return response.status_code, response.json()

        with ThreadPoolExecutor(max_workers=20) as pool:
            results = list(pool.map(submit, range(20)))
        accepted = [body for code, body in results if code == 202]
        assert len(accepted) == 5 and sum(code == 429 for code, _ in results) == 15, [code for code, _ in results]
        for item in accepted:
            def completed():
                status = other.get(self.base + f"/analyses/{item['analysisId']}/status", timeout=15).json()
                return status if status.get("status") in {"Completed", "Failed"} else None
            status = self.wait(completed, 300)
            assert status["status"] == "Completed" and len(status["result"]["predictions"]) == 3
        usage = other.get(self.base + "/subscriptions/usage", timeout=15).json()
        assert usage["analysesUsed"] == 5 and usage["remaining"] == 0
        history = other.get(self.base + "/analyses", timeout=15).json()
        assert history["total"] == 5
        free_rows = self.sql(f"SELECT Status,COUNT(*) Records FROM UsageRecords WHERE UserId='{session['user']['id']}' GROUP BY Status FOR JSON PATH")
        assert free_rows == [{"Status": "Consumed", "Records": 5}]
        deleted = self.sql(f"SELECT Id FROM Analyses WHERE UserId='{session['user']['id']}' AND JobId='{accepted[0]['analysisId']}' FOR JSON PATH")[0]["Id"]
        assert other.delete(self.base + f"/analyses/{deleted}", timeout=15).status_code == 204
        assert other.get(self.base + "/subscriptions/usage", timeout=15).json()["remaining"] == 0
        assert other.get(self.base + "/analyses", timeout=15).json()["total"] == 4
        assert other.post(self.base + "/auth/logout", timeout=15).status_code == 204
        assert other.get(self.base + "/auth/me", timeout=15).status_code == 401
        self.record("20 concurrent real FREE requests: exactly 5 accepted and completed, 15 quota denials; deletion did not refund usage and logout revoked session", accepted=5, quotaRejected=15, realAiCompleted=5, freeUsage=free_rows, deletedOwnTestResult=True, remainingAfterDelete=0)

    def run(self):
        try:
            self.configure()
            self.account()
            order = self.payment(test_reorg=True)
            if not self.args.skip_ai:
                self.analysis(sorted((ROOT / "sample_images").glob("*.jpg"))[0], "image")
                self.analysis(sorted((ROOT / "sample_audio").glob("*.wav"))[0], "audio")
                assert self.request("GET", "/analyses")["total"] == 2
                self.record("Authenticated history contains both real analyses; PRO remaining quota is 98")
                self.verify_free_limits_and_privacy()
            self.sql(f"UPDATE UserSubscriptions SET StartDate=DATEADD(day,-31,SYSDATETIMEOFFSET()),EndDate=DATEADD(second,-1,SYSDATETIMEOFFSET()) WHERE PaymentOrderId='{order['id']}'; SELECT Id FROM UserSubscriptions WHERE PaymentOrderId='{order['id']}' FOR JSON PATH")
            assert self.request("GET", "/subscriptions/me")["plan"] == "FREE"
            self.wait(lambda: self.sql(f"SELECT Status FROM UserSubscriptions WHERE PaymentOrderId='{order['id']}' FOR JSON PATH")[0]["Status"] == "Expired", 20)
            if not self.args.skip_ai:
                assert self.request("GET", "/analyses")["total"] == 2
            self.record("Expiry background service persisted Expired; immediate FREE fallback preserved history")
            self.payment(plan=2, check_pending=True)
            self.capture_evidence()
            self.report["outcome"] = "passed"
            self.report["completeAiBlockchainScenario"] = not self.args.skip_ai
            self.report["completedAt"] = datetime.now(timezone.utc).isoformat()
            self.record("Real local blockchain verification protocol completed")
        except Exception as error:
            self.report["outcome"] = "failed"
            self.report["error"] = f"{type(error).__name__}: {error}"
            self.save()
            raise
        finally:
            if self.args.docker and self.docker_started:
                try:
                    (self.artifacts / "docker-services.log").write_text(self.compose("logs", "--no-color", "--tail", "200", "central", "worker", "ai", "migrate", "sql", "rabbitmq", "anvil"), encoding="utf-8")
                    if not self.args.keep_services:
                        self.compose("down", "--timeout", "30")
                except (RuntimeError, subprocess.TimeoutExpired) as error:
                    self.report["dockerCleanupError"] = str(error)
            if not self.args.keep_services:
                for process in reversed(self.processes):
                    process.terminate()
                for process in self.processes:
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        process.kill()
            else:
                (self.artifacts / "service-processes.json").write_text(json.dumps([{"pid": p.pid, "args": p.args} for p in self.processes], indent=2), encoding="utf-8")
            for log in self.logs:
                log.close()
            self.save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Справжній Anvil + MS SQL + RabbitMQ + Hugging Face протокол без реальних коштів.")
    parser.add_argument("--rpc", default="http://127.0.0.1:8545")
    parser.add_argument("--port", type=int, default=5100)
    parser.add_argument("--skip-ai", action="store_true", help="Лише блокчейн і SQL; не є доказом повного AI-сценарію.")
    parser.add_argument("--keep-services", action="store_true")
    parser.add_argument("--docker", action="store_true", help="Справжній сценарій в ізольованому Docker Compose; робочі volumes не змінюються.")
    Protocol(parser.parse_args()).run()
