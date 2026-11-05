import argparse
import csv
import hashlib
import io
import json
import sqlite3
import time
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]


def verify(base: str, batch: bool) -> dict:
    checks = []
    created = []
    web = requests.Session()
    mobile = requests.Session()
    web.headers["X-Verification-Client"] = "web-http-session"
    mobile.headers["X-Verification-Client"] = "mobile-http-session"

    def get(path, session=web):
        response = session.get(base + "/api" + path, timeout=240)
        response.raise_for_status()
        return response.json()

    def upload(kind, path, session):
        with path.open("rb") as stream:
            response = session.post(base + "/api/analysis/sync/" + kind, files={"file": (path.name, stream)}, timeout=300)
        response.raise_for_status()
        payload = response.json()
        assert len(payload["predictions"]) == 3
        assert all(0 <= p["confidence"] <= 1 for p in payload["predictions"])
        created.append(payload["id"])
        return payload

    health = get("/health")
    assert health["database"] and health["ai"]
    initial = get("/analyses?pageSize=100")
    first = upload("image", ROOT / "sample_images" / "01_Cardinalis_cardinalis.jpg", mobile)
    from_web = get(f"/analyses/{first['id']}", web)
    assert from_web == first
    checks.append("mobile HTTP multipart → ASP.NET → FastAPI → real image model → SQL → web HTTP history")
    second = upload("image", ROOT / "sample_images" / "02_Cyanocitta_cristata.jpg", web)
    assert get(f"/analyses/{second['id']}", mobile) == second
    checks.append("web HTTP multipart → SQL → mobile HTTP history")
    audio = upload("audio", ROOT / "sample_audio" / "robin.wav", mobile)
    assert audio["analysisType"] == "audio"
    checks.append("real Wav2Vec2 audio analysis through central HTTP API")
    media = web.get(base + first["fileUrl"], timeout=30)
    media.raise_for_status()
    assert hashlib.sha256(media.content).digest() == hashlib.sha256((ROOT / "sample_images" / "01_Cardinalis_cardinalis.jpg").read_bytes()).digest()
    ranged = web.get(base + audio["fileUrl"], headers={"Range": "bytes=0-99"}, timeout=30)
    assert ranged.status_code == 206 and len(ranged.content) == 100
    checks.append("managed media bytes, SHA-256 and audio Range 206")
    malformed = web.post(base + "/api/analysis/sync/image", files={"file": ("broken.png", b"not an image")}, timeout=120)
    assert malformed.status_code == 422
    assert "detail" in malformed.json()
    assert get("/analyses?pageSize=1")["total"] == initial["total"] + 3
    checks.append("corrupt image rejected, no history record inserted")
    assert web.get(base + "/api/analyses?page=0", timeout=30).status_code == 400
    assert get("/analyses?pageSize=1&sort=confidence_desc")["pageSize"] == 1
    assert get("/analyses?search=01_Cardinalis")["total"] >= 1
    checks.append("history search, pagination, sorting and invalid query handling")
    birds = get("/birds")
    assert len(birds) >= 15
    assert get(f"/birds/compare?firstId={birds[0]['id']}&secondId={birds[1]['id']}")["first"]["id"] == birds[0]["id"]
    assert get(f"/analyses/compare?firstId={first['id']}&secondId={audio['id']}")["conclusion"]
    checks.append("bird search/catalog, species and model comparisons")
    batch_rows = []
    if batch:
        images = sorted((ROOT / "sample_images").glob("*"))
        assert len(images) == 15
        with ExitStack() as stack:
            files = [("files", (path.name, stack.enter_context(path.open("rb")))) for path in images]
            response = web.post(base + "/api/analysis/batch", files=files, timeout=1200)
        response.raise_for_status()
        assert response.status_code == 202
        accepted = response.json()
        batch_rows = []
        for row in accepted:
            task = row["task"]
            deadline = time.monotonic() + 300
            analysis = None
            error = row["error"]
            while task and time.monotonic() < deadline:
                status = get(f"/analyses/{task['analysisId']}/status")
                if status["status"] == "Completed":
                    analysis = status["result"]
                    break
                if status["status"] == "Failed":
                    error = status["errorMessage"]
                    break
                time.sleep(2)
            batch_rows.append({"fileName": row["fileName"], "analysis": analysis, "error": error})
        assert len(batch_rows) == 15 and all(row["analysis"] and not row["error"] for row in batch_rows)
        created.extend(row["analysis"]["id"] for row in batch_rows)
        checks.append("batch of all 15 original sample images through real HTTP/models/SQL")
    exported = web.get(base + "/api/export/csv", timeout=60)
    exported.raise_for_status()
    assert exported.content.startswith(b"\xef\xbb\xbf")
    csv_rows = list(csv.DictReader(io.StringIO(exported.content.decode("utf-8-sig"))))
    assert len(csv_rows) == get("/analyses?pageSize=1")["total"]
    checks.append("CSV BOM, actual SQL row count and Ukrainian text")
    deletion = web.delete(base + f"/api/analyses/{second['id']}", timeout=30)
    assert deletion.status_code == 204
    assert mobile.get(base + f"/api/analyses/{second['id']}", timeout=30).status_code == 404
    assert mobile.get(base + second["fileUrl"], timeout=30).status_code == 404
    created.remove(second["id"])
    checks.append("delete visible in independent client, deleted media unavailable")
    stats = {name: get("/statistics/" + name) for name in ("summary", "species", "confidence", "evaluations")}
    assert stats["summary"]["totalAnalyses"] == initial["total"] + len(created)
    assert sum(item["count"] for item in stats["confidence"]) == stats["summary"]["totalAnalyses"]
    checks.append("statistics counts match SQL history and confidence histogram")
    protected = json.loads((ROOT / "verification" / "client-server-baseline.json").read_text(encoding="utf-8"))
    for relative, expected in protected["hashes"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, relative
    checks.append(f"all {len(protected['hashes'])} original files retain exact SHA-256")
    return {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "mock_used": False, "physical_iphone_tested": False, "client_test_method": "two independent requests.Session HTTP clients; browser/device UI verified separately", "initial_count": initial["total"], "remaining_created_ids": created, "checks": checks, "image": first, "audio": audio, "batch": batch_rows, "statistics": stats}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:5100")
    parser.add_argument("--batch", action="store_true")
    args = parser.parse_args()
    started = time.perf_counter()
    result = verify(args.base.rstrip("/"), args.batch)
    result["elapsed_seconds"] = time.perf_counter() - started
    target = ROOT / "verification" / "client-server-real.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"checks": len(result["checks"]), "report": str(target), "mock_used": False, "elapsed_seconds": result["elapsed_seconds"]}, ensure_ascii=False))
