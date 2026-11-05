import hashlib
import json
import re
import tokenize
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OWNED = ["ai-server", "central-server", "central-server.Tests", "web-app/src", "mobile-app/src", "shared"]
IGNORED = {"node_modules", "bin", "obj", "__pycache__", ".test-artifacts", ".expo"}


def main():
    baseline = json.loads((ROOT / "verification" / "client-server-baseline.json").read_text(encoding="utf-8"))
    changed = [name for name, expected in baseline["hashes"].items() if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected]
    assert not changed, changed
    comments = []
    paths = []
    for folder in OWNED:
        paths.extend(path for path in (ROOT / folder).rglob("*") if path.is_file() and not IGNORED.intersection(path.relative_to(ROOT / folder).parts))
    paths.extend(ROOT / name for name in ["mobile-app/App.tsx", "mobile-app/index.ts", "mobile-app/metro.config.js", "birdlab/config.py", "birdlab/models.py"])
    paths.extend((ROOT / "scripts").glob("*.py"))
    paths.extend((ROOT / "scripts").glob("*.ps1"))
    paths.extend((ROOT / "tests").glob("*.py"))
    for path in paths:
        if path.suffix == ".py":
            with path.open("rb") as stream:
                comments.extend(f"{path.relative_to(ROOT)}:{token.start[0]}" for token in tokenize.tokenize(stream.readline) if token.type == tokenize.COMMENT)
        elif path.suffix in {".ts", ".tsx", ".cs", ".js", ".ps1"}:
            for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
                if re.match(r"^\s*(//|/\*|\*/|<!--)", line) or path.suffix == ".ps1" and line.lstrip().startswith("#"):
                    comments.append(f"{path.relative_to(ROOT)}:{line_number}")
    assert not comments, comments
    map_path = ROOT / "data" / "submission_uploads.json"
    if map_path.exists():
        for target, entry in json.loads(map_path.read_text(encoding="utf-8")).items():
            assert hashlib.sha256((ROOT / entry["source"]).read_bytes()).hexdigest() == entry["sha256"]
            assert hashlib.sha256((ROOT / target).read_bytes()).hexdigest() == entry["sha256"]
    result = {"original_files_verified": len(baseline["hashes"]), "original_files_changed": changed, "source_comments": comments, "source_files_scanned": len(paths)}
    (ROOT / "verification" / "delivery-check.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
