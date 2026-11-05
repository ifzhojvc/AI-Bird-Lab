import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:5100"


def main():
    health = requests.get(BASE + "/api/health", timeout=15)
    health.raise_for_status()
    swagger = requests.get(BASE + "/swagger/v1/swagger.json", timeout=30)
    swagger.raise_for_status()
    schema = swagger.json()
    for route in ("/api/analysis/image", "/api/analysis/audio", "/api/analysis/batch"):
        assert "202" in schema["paths"][route]["post"]["responses"]
    assert "/api/analyses/{id}/status" in schema["paths"]
    assert "SummaryDto" in schema["components"]["schemas"]
    assert "totalAnalyses" in schema["components"]["schemas"]["SummaryDto"]["properties"]
    before = requests.get(BASE + "/api/analyses?pageSize=1", timeout=30).json()["total"]
    path = ROOT / "sample_images" / "01_Cardinalis_cardinalis.jpg"
    with path.open("rb") as stream:
        result = requests.post(BASE + "/api/analysis/sync/image", files={"file": (path.name, stream)}, timeout=240)
    result.raise_for_status()
    payload = result.json()
    assert len(payload["predictions"]) == 3
    saved = requests.get(BASE + f"/api/analyses/{payload['id']}", timeout=30)
    assert saved.json() == payload
    deletion = requests.delete(BASE + f"/api/analyses/{payload['id']}", timeout=30)
    assert deletion.status_code == 204
    statistics = {}
    for name in ("summary", "species", "confidence", "evaluations"):
        response = requests.get(BASE + "/api/statistics/" + name, timeout=30)
        response.raise_for_status()
        statistics[name] = response.json()
    assert statistics["summary"]["totalAnalyses"] == before
    report = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "mock_used": False, "health": health.json(), "openapi_paths": len(schema["paths"]), "swagger_statistics_schema": True, "fresh_image_saved_read_deleted": True, "history_count": before, "statistics": statistics}
    (ROOT / "verification" / "rabbitmq-sync-compat.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"health": "ok", "swagger": True, "real_image_cycle": True, "history_count": before}))


if __name__ == "__main__":
    main()
