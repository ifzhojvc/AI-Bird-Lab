import hashlib
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def snapshot() -> dict:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = ROOT / "data" / "backups" / stamp
    backup.mkdir(parents=True)
    source = ROOT / "birds.db"
    with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as connection:
        with sqlite3.connect(backup / "birds.db") as destination:
            connection.backup(destination)
        counts = {name: connection.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0] for name in ("bird_info", "analyses", "predictions", "evaluations")}
        paths = [row[0] for row in connection.execute("SELECT file_path FROM analyses")]
    shutil.copy2(ROOT / "bird_analysis.csv", backup / "bird_analysis.csv")
    files = [ROOT / "birds.db", ROOT / "bird_analysis.csv", *sorted((ROOT / "uploads").glob("*")), *sorted((ROOT / "sample_images").glob("*")), *sorted((ROOT / "sample_audio").glob("*"))]
    hashes = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in files if path.is_file()}
    for relative in paths:
        path = (ROOT / relative).resolve()
        if not path.is_relative_to((ROOT / "uploads").resolve()) or not path.is_file():
            raise RuntimeError(f"Некоректний або відсутній файл: {relative}")
        destination = backup / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    result = {"timestamp_utc": stamp, "backup": str(backup), "counts": counts, "hashes": hashes}
    (backup / "manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "verification" / "client-server-baseline.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    result = snapshot()
    print(json.dumps({"backup": result["backup"], "counts": result["counts"], "protected_files": len(result["hashes"])}, ensure_ascii=False))
