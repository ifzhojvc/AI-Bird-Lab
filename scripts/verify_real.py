import argparse
import csv
import io
import json
import platform
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from birdlab.config import AUDIO_MODEL, AUDIO_REVISION, CSV_PATH, DB_PATH, IMAGE_MODEL, IMAGE_REVISION, SAMPLE_DIR, UPLOAD_DIR
from birdlab.errors import BirdLabError
from birdlab.export import write_csv
from birdlab.files import load_audio, read_file, sha256
from birdlab.repository import Repository
from birdlab.service import AnalysisService, sample_manifest, verified_evaluation
from birdlab.statistics import build_charts, filter_gallery, quality_metrics, summarize


def main() -> None:
    parser = argparse.ArgumentParser(description="Справжній протокол перевірки без mocks")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    repository = Repository(DB_PATH, UPLOAD_DIR)
    service = AnalysisService(repository, offline=args.offline, export_path=CSV_PATH)
    evidence = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(), "packages": {name: version(name) for name in ("torch", "transformers", "streamlit", "Pillow", "librosa", "soundfile", "numpy", "pandas", "plotly")}, "mock_used": False, "offline": args.offline, "models": {"image": {"id": IMAGE_MODEL, "revision": IMAGE_REVISION}, "audio": {"id": AUDIO_MODEL, "revision": AUDIO_REVISION}}, "images": [], "errors": []}
    rows = sample_manifest()
    if len(rows) < 15 or len({row["scientific_name"] for row in rows}) < 15:
        raise RuntimeError("Потрібні 15 реальних фотографій 15 різних видів")
    for row in rows:
        name = row["file_name"]
        try:
            data = read_file(SAMPLE_DIR / name)
            evaluation = verified_evaluation(row, data)
            existing = [r for r in repository.all(kind="image") if r["file_hash"] == sha256(data) and r["model_id"] == IMAGE_MODEL and r["model_revision"] == IMAGE_REVISION and repository.get(r["id"])["evaluation"]]
            analysis_id = existing[0]["id"] if existing else service.analyze(data, name, "image", evaluation)
            record = repository.get(analysis_id)
            assert len(record["predictions"]) == 3 and repository.media_path(record).read_bytes() == data
            evidence["images"].append({"id": analysis_id, "file_name": name, "sha256": sha256(data), "expected_label": row["model_label"], "predictions": record["predictions"], "top1_correct": bool(record["evaluation"]["top1_correct"]), "top3_correct": bool(record["evaluation"]["top3_correct"]), "elapsed_seconds": record["elapsed_seconds"]})
            print(name, "=>", record["predicted_species"], f"{record['confidence']:.6f}", "Top-1:", record["evaluation"]["top1_correct"], flush=True)
        except BirdLabError as exc:
            evidence["errors"].append({"file": name, "error": str(exc)})
            print("ПОМИЛКА", name, str(exc), flush=True)
    audio_path = ROOT / "sample_audio" / "robin.wav"
    if audio_path.exists():
        try:
            data = read_file(audio_path)
            existing = [r for r in repository.all(kind="audio") if r["file_hash"] == sha256(data) and r["model_id"] == AUDIO_MODEL and r["model_revision"] == AUDIO_REVISION]
            analysis_id = existing[0]["id"] if existing else service.analyze(data, audio_path.name, "audio")
            record = repository.get(analysis_id)
            audio = load_audio(data, audio_path.name)
            assert len(record["predictions"]) == 3 and audio.sample_rate == 16000
            evidence["audio"] = {"id": analysis_id, "file_name": audio_path.name, "sha256": sha256(data), "predictions": record["predictions"], "metadata": record["metadata"], "elapsed_seconds": record["elapsed_seconds"], "accuracy_evaluated": False, "limitation": "Robin is outside this model's labels; this is an execution and persistence check, not recognition accuracy."}
            print("Аудіо:", record["predictions"], flush=True)
        except BirdLabError as exc:
            evidence["errors"].append({"file": audio_path.name, "error": str(exc)})
    else:
        evidence["audio"] = {"tested": False, "reason": "Реальний файл відсутній"}
    records = repository.all()
    write_csv(records, CSV_PATH)
    exported = list(csv.DictReader(io.StringIO(CSV_PATH.read_text(encoding="utf-8-sig"))))
    assert len(exported) == len(records)
    assert CSV_PATH.read_bytes().startswith(b"\xef\xbb\xbf")
    charts = build_charts(records)
    assert len(charts) == 5
    for chart in charts.values():
        json.loads(chart.to_json())
    gallery = filter_gallery(records)
    assert len(gallery) == len([r for r in records if r["analysis_type"] == "image"])
    evidence["quality"] = quality_metrics(repository.evaluations())
    evidence["summary"] = {key: value for key, value in summarize(records).items() if key not in ("max_record", "min_record")}
    evidence["checks"] = {"sqlite_save_and_read": True, "top3_stored": all(len(repository.get(r["id"])["predictions"]) == 3 for r in records), "csv_bom": True, "csv_rows": len(exported), "plotly_charts": len(charts), "gallery_filter": True, "sample_hashes": len(evidence["images"]), "audio_real_inference": "predictions" in evidence.get("audio", {})}
    evidence["passed"] = len(evidence["images"]) >= 15 and not evidence["errors"] and evidence["checks"]["audio_real_inference"]
    out = ROOT / "verification" / "real_run.json"
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": evidence["passed"], "checks": evidence["checks"], "quality": evidence["quality"]}, ensure_ascii=False, indent=2), flush=True)
    if not evidence["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
