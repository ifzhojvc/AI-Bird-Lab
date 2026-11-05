import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / ".test-artifacts" / "before-subscriptions"


def sql(query, database="AIBirdLab"):
    server = os.environ.get("BIRDLAB_SQL_SERVER", r".\SQLEXPRESS")
    command = ["sqlcmd", "-S", server, "-E", "-C", "-l", "10", "-b", "-y", "0", "-w", "65535", "-f", "65001", "-d", database, "-Q", "SET NOCOUNT ON; " + query]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8-sig", timeout=60)
    if result.returncode:
        raise RuntimeError(result.stderr[-1500:])
    output = "".join(result.stdout.splitlines()).strip()
    start = output.find("[")
    return json.loads(output[start:output.rfind("]") + 1]) if start >= 0 else []


def snapshot():
    path = BASELINE / "mssql.json"
    if path.exists():
        raise RuntimeError("SQL baseline already exists and will not be overwritten.")
    records = {table: sql(f"SELECT * FROM {table} ORDER BY Id FOR JSON PATH, INCLUDE_NULL_VALUES") for table in ("Analyses", "Predictions", "Birds")}
    records["Evaluations"] = sql("SELECT * FROM Evaluations ORDER BY AnalysisId FOR JSON PATH, INCLUDE_NULL_VALUES")
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"snapshot": str(path), "counts": {name: len(rows) for name, rows in records.items()}}, ensure_ascii=False))


def verify():
    before = json.loads((BASELINE / "mssql.json").read_text(encoding="utf-8"))
    counts = {}
    for table, original in before.items():
        key = "AnalysisId" if table == "Evaluations" else "Id"
        rows = sql(f"SELECT * FROM {table} ORDER BY {key} FOR JSON PATH, INCLUDE_NULL_VALUES")
        current = {row[key]: row for row in rows}
        for row in original:
            assert row[key] in current, (table, row[key], "missing")
            assert {name: current[row[key]][name] for name in row} == row, (table, row[key], "changed")
            if table == "Analyses":
                assert current[row[key]].get("UserId") is None
        counts[table] = {"before": len(original), "after": len(rows), "original_rows_unchanged": True}
    manifest = json.loads((BASELINE / "manifest.json").read_text(encoding="utf-8"))["files"]
    protected = []
    for name, digest in manifest.items():
        if name in {"app.py", "birds.db", "bird_analysis.csv", "sample_manifest.csv"} or name.startswith(("birdlab/", "uploads/", "sample_images/", "sample_audio/", "central-server/storage/")) or name in {"data/birds.json", "data/model_selection.json"}:
            path = ROOT / name
            assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
            protected.append(name)
    result = {"sql": counts, "protected_files": len(protected), "all_unchanged": True, "legacy_owner_assigned": False}
    (ROOT / "verification" / "subscriptions-preservation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["snapshot", "verify"])
    args = parser.parse_args()
    snapshot() if args.action == "snapshot" else verify()
