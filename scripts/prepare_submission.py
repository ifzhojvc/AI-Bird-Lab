import argparse
import hashlib
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRECTORIES = {".venv", ".cache", ".pytest_cache", "__pycache__", ".test-artifacts", "node_modules", "bin", "obj", "dist", ".expo", ".git", ".tools", ".codex", ".agents", ".aws", ".ssh", "submission", "submission-rabbitmq", ".worker-state", "rabbitmq-data", "worker-state", "keystore", "keystores"}
EXCLUDE_PREFIXES = {"data/backups", "central-server/storage", "contracts/cache", "contracts/out", "contracts/broadcast"}


def source_files():
    for folder, directories, files in os.walk(ROOT):
        relative = Path(folder).relative_to(ROOT).as_posix()
        directories[:] = [d for d in directories if d not in EXCLUDE_DIRECTORIES and f"{relative}/{d}".removeprefix("./") not in EXCLUDE_PREFIXES]
        for name in sorted(files):
            path = Path(folder) / name
            if name.startswith(".env") and name != ".env.example":
                continue
            if path.relative_to(ROOT).as_posix() == ".streamlit/secrets.toml" or name.startswith(("UTC--", "anvil-state")):
                continue
            if path.suffix.lower() in {".pyc", ".log", ".tmp", ".tsbuildinfo", ".mdf", ".ldf", ".zip", ".rar", ".safetensors", ".bin", ".pt", ".pth", ".key", ".pem", ".p12", ".pfx", ".keystore"} or name.endswith((".db-wal", ".db-shm")):
                continue
            yield path


def main():
    parser = argparse.ArgumentParser(description="Підготовка вихідних файлів без архівування та без видалення даних.")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--refresh", action="store_true", help="Підготувати нову копію та зберегти попередню у .test-artifacts без видалення.")
    args = parser.parse_args()
    files = list(source_files())
    canonical = {}
    for path in files:
        if path.parent.name in {"sample_images", "sample_audio"}:
            canonical.setdefault(hashlib.sha256(path.read_bytes()).hexdigest(), path)
    duplicate_uploads = {}
    for path in files:
        if path.parent == ROOT / "uploads":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest in canonical:
                duplicate_uploads[path.relative_to(ROOT).as_posix()] = {"source": canonical[digest].relative_to(ROOT).as_posix(), "sha256": digest}
    mapping = ROOT / "data" / "submission_uploads.json"
    mapping.write_text(json.dumps(duplicate_uploads, ensure_ascii=False, indent=2), encoding="utf-8")
    files = [p for p in source_files() if p.relative_to(ROOT).as_posix() not in duplicate_uploads]
    total = sum(p.stat().st_size for p in files)
    if total >= 25_000_000:
        raise SystemExit(f"Вихідні файли займають {total} байтів: перевищено 25 МБ. Перевірте зайві артефакти; користувацькі дані не видаляйте.")
    result = {"files": len(files), "bytes": total, "megabytes": round(total / 1_000_000, 3), "under_25_mb_uncompressed": True, "archive_created": False, "duplicate_upload_copies_omitted": len(duplicate_uploads), "restore_command": ".venv/Scripts/python.exe scripts/restore_uploads.py"}
    if args.output:
        destination = args.output.resolve()
        if destination not in {ROOT / "submission", ROOT / "submission-rabbitmq"}:
            raise SystemExit("Дозволені папки результату: submission або submission-rabbitmq у корені проєкту.")
        if destination.is_symlink():
            raise SystemExit("Папка результату не може бути символічним посиланням.")
        if destination.exists() and not args.refresh:
            raise SystemExit("Папка результату вже існує; скрипт нічого не перезаписує.")
        staging = ROOT / ".test-artifacts" / ("submission-stage-" + uuid.uuid4().hex)
        staging.mkdir(parents=True)
        for source in files:
            target = staging / source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        result["directory"] = str(destination)
        result["hashes"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        (staging / "submission-manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        actual_size = sum(p.stat().st_size for p in staging.rglob("*") if p.is_file())
        if actual_size >= 25_000_000:
            raise SystemExit("Комплект разом із маніфестом перевищує 25 МБ. Попередню папку не змінено.")
        for source in files:
            relative = source.relative_to(ROOT)
            if hashlib.sha256((staging / relative).read_bytes()).hexdigest() != result["hashes"][str(relative)]:
                raise SystemExit(f"Помилка копіювання: {relative}")
        if destination.exists():
            backup = ROOT / ".test-artifacts" / (destination.name + "-previous-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
            if destination.resolve().parent != ROOT or not backup.resolve().is_relative_to((ROOT / ".test-artifacts").resolve()):
                raise SystemExit("Некоректні шляхи оновлення комплекту.")
            destination.rename(backup)
            result["previous_copy_preserved"] = str(backup)
        try:
            staging.rename(destination)
        except Exception:
            if 'backup' in locals() and backup.exists() and not destination.exists():
                backup.rename(destination)
            raise
        result["actual_bytes_including_manifest"] = actual_size
    (ROOT / "verification" / "submission-size.json").write_text(json.dumps({key: value for key, value in result.items() if key != "hashes"}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "hashes"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
