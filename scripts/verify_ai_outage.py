import json
from datetime import datetime, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:5100"


def main():
    initial = requests.get(BASE + "/api/analyses?pageSize=1", timeout=30).json()["total"]
    original_files = {p.name for p in (ROOT / "central-server" / "storage").iterdir() if p.is_file()}
    health = requests.get(BASE + "/api/health", timeout=15)
    assert health.status_code == 503 and health.json()["database"] is True and health.json()["ai"] is False, "Спочатку зупиніть лише власний AI-сервер для перевірки збою."
    path = ROOT / "sample_images" / "01_Cardinalis_cardinalis.jpg"
    with path.open("rb") as stream:
        response = requests.post(BASE + "/api/analysis/sync/image", files={"file": (path.name, stream)}, timeout=30)
    assert response.status_code == 502 and "detail" in response.json()
    final = requests.get(BASE + "/api/analyses?pageSize=1", timeout=30).json()["total"]
    final_files = {p.name for p in (ROOT / "central-server" / "storage").iterdir() if p.is_file()}
    assert final == initial and final_files == original_files
    result = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "actual_ai_process_stopped": True, "mock_used": False, "health_status": 503, "prediction_status": 502, "history_count_before": initial, "history_count_after": final, "storage_unchanged": True, "response": response.json()}
    (ROOT / "verification" / "ai-outage.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"health": 503, "analysis": 502, "no_history_or_file_saved": True}))


if __name__ == "__main__":
    main()
