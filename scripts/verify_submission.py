import argparse
import hashlib
import json
import shutil
import sqlite3
import uuid
from pathlib import Path

from restore_uploads import restore


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description="Перевірка компактного комплекту та точного відновлення даних без зміни основного проєкту.")
    parser.add_argument("--directory", choices=["submission", "submission-rabbitmq"], default="submission")
    args = parser.parse_args()
    package = ROOT / args.directory
    manifest = json.loads((package / "submission-manifest.json").read_text(encoding="utf-8"))
    for relative, expected in manifest["hashes"].items():
        assert hashlib.sha256((package / relative).read_bytes()).hexdigest() == expected, relative
    actual_bytes = sum(path.stat().st_size for path in package.rglob("*") if path.is_file())
    assert actual_bytes < 25_000_000
    target = ROOT / ".test-artifacts" / ("submission-roundtrip-" + uuid.uuid4().hex)
    target.mkdir(parents=True)
    for folder in ("sample_images", "sample_audio", "data"):
        shutil.copytree(package / folder, target / folder)
    shutil.copy2(package / "birds.db", target / "birds.db")
    if (package / "uploads").exists():
        shutil.copytree(package / "uploads", target / "uploads")
    restored = restore(target)
    with sqlite3.connect((target / "birds.db").as_uri() + "?mode=ro", uri=True) as connection:
        rows = connection.execute("SELECT file_path, file_hash FROM analyses").fetchall()
        for relative, digest in rows:
            assert hashlib.sha256((target / relative).read_bytes()).hexdigest() == digest
        predictions = connection.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
        evaluations = connection.execute("SELECT COUNT(*) FROM evaluations").fetchone()[0]
    result = {"source_directory": str(package), "actual_bytes_including_manifest": actual_bytes, "megabytes": round(actual_bytes / 1_000_000, 3), "archive_created": False, "hashes_verified": len(manifest["hashes"]), "uploads_restored_in_isolated_test": restored, "legacy_analyses_with_verified_files": len(rows), "predictions": predictions, "evaluations": evaluations, "second_restore_count": restore(target)}
    report_name = "rabbitmq-submission-roundtrip.json" if args.directory == "submission-rabbitmq" else "submission-roundtrip.json"
    (ROOT / "verification" / report_name).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
