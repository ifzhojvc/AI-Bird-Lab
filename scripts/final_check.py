import ast
import csv
import hashlib
import importlib
import io
import json
import subprocess
import sys
import tokenize
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from birdlab.config import CSV_PATH, DB_PATH, UPLOAD_DIR
from birdlab.repository import Repository
from birdlab.service import sample_manifest
from birdlab.statistics import build_charts, filter_gallery


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    sources = [ROOT / "app.py"] + sorted((ROOT / "birdlab").rglob("*.py")) + sorted((ROOT / "scripts").glob("*.py")) + sorted((ROOT / "tests").glob("*.py"))
    comments = []
    for path in sources:
        source = path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(path))
        comments.extend(f"{path.relative_to(ROOT)}:{token.start[0]}" for token in tokenize.generate_tokens(io.StringIO(source).readline) if token.type == tokenize.COMMENT)
    assert not comments, comments
    imports = []
    for path in [ROOT / "app.py"] + sorted((ROOT / "birdlab").rglob("*.py")):
        parts = list(path.relative_to(ROOT).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        name = ".".join(parts)
        importlib.import_module(name)
        imports.append(name)
    dependency_check = subprocess.run([sys.executable, "-m", "pip", "check"], capture_output=True, text=True, check=False)
    assert dependency_check.returncode == 0, dependency_check.stdout + dependency_check.stderr
    repository = Repository(DB_PATH, UPLOAD_DIR)
    with repository.connection() as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
        prediction_count = connection.execute("SELECT count(*) FROM predictions").fetchone()[0]
    assert integrity == "ok" and not foreign_keys
    records = repository.all()
    assert prediction_count == len(records) * 3
    for record in records:
        assert digest(repository.media_path(record)) == record["file_hash"]
        assert len(repository.get(record["id"])["predictions"]) == 3
    manifest = sample_manifest()
    assert len(manifest) >= 15 and len({row["scientific_name"] for row in manifest}) >= 15
    for row in manifest:
        assert digest(ROOT / "sample_images" / row["file_name"]) == row["sha256"]
        assert row["source_url"].startswith("https://commons.wikimedia.org/")
        assert row["license"] and row["author"] and row["license_url"]
    assert CSV_PATH.read_bytes().startswith(b"\xef\xbb\xbf")
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as stream:
        exported = list(csv.DictReader(stream))
    assert len(exported) == len(records)
    by_id = {str(record["id"]): record for record in records}
    for row in exported:
        record = by_id[row["analysis_id"]]
        if record["analysis_type"] == "image":
            assert row["image_name"] == record["original_name"] and row["predicted_species"] == record["predicted_species"]
            assert float(row["confidence"]) == record["confidence"] and row["audio_name"] == ""
        else:
            assert row["image_name"] == row["predicted_species"] == row["confidence"] == ""
            assert row["audio_name"] == record["original_name"] and row["audio_predicted_species"] == record["predicted_species"]
            assert float(row["audio_confidence"]) == record["confidence"]
    charts = build_charts(records)
    assert len(charts) == 5 and all(chart.to_json() for chart in charts.values())
    photos = filter_gallery(records)
    assert len(photos) == sum(row["analysis_type"] == "image" for row in records)
    required = ["app.py", "requirements.txt", "requirements-lock.txt", "README.md", "report.md", "birds.db", "bird_analysis.csv", "sample_manifest.csv", ".gitignore", ".streamlit/config.toml"]
    assert all((ROOT / name).is_file() for name in required)
    result = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "passed": True, "python_files_parsed": len(sources), "python_comments": comments, "modules_imported": imports, "pip_check": dependency_check.stdout.strip(), "sqlite_integrity": integrity, "foreign_key_errors": len(foreign_keys), "analysis_rows": len(records), "prediction_rows": prediction_count, "evaluation_rows": len(repository.evaluations()), "sample_images": len(manifest), "unique_ground_truth_species": len({row["scientific_name"] for row in manifest}), "csv_rows": len(exported), "csv_bom": True, "plotly_charts": len(charts), "media_hashes_verified": len(records), "files_sha256": {name: digest(ROOT / name) for name in ("birds.db", "bird_analysis.csv", "sample_manifest.csv")}}
    (ROOT / "verification" / "final_checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
