import hashlib
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP = {"node_modules", ".venv", ".cache", ".git", "bin", "obj", "dist", ".expo", "__pycache__", ".test-artifacts", "submission", "submission-rabbitmq", ".pytest_cache"}


def capture():
    destination = ROOT / ".test-artifacts" / "before-subscriptions"
    if destination.exists():
        raise SystemExit("Baseline already exists; it must not be overwritten.")
    destination.mkdir(parents=True)
    files = {}
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if not path.is_file() or any(part in SKIP for part in relative.parts) or relative.parts[:2] == ("data", "backups"):
            continue
        files[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        if relative.parts[0] in {"central-server", "central-server.Tests", "shared", "web-app", "mobile-app", "scripts"} or path.name in {"README.md", "report.md", "compose.yaml", ".gitignore", ".env.example"}:
            if "storage" not in relative.parts:
                target = destination / "source" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
    with sqlite3.connect((ROOT / "birds.db").as_uri() + "?mode=ro", uri=True) as connection:
        with sqlite3.connect(destination / "birds.db") as backup:
            connection.backup(backup)
        counts = {table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0] for table in ("bird_info", "analyses", "predictions", "evaluations")}
    result = {"captured_at": datetime.now(timezone.utc).isoformat(), "files": files, "sqlite_counts": counts}
    (destination / "manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"files": len(files), "sqlite_counts": counts, "baseline": str(destination)}, ensure_ascii=False))


if __name__ == "__main__":
    capture()
