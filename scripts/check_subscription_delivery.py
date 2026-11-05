import hashlib
import io
import json
import tokenize
from pathlib import Path

from prepare_submission import ROOT


def main():
    package = ROOT / "submission"
    manifest = json.loads((package / "submission-manifest.json").read_text(encoding="utf-8"))
    blocked_parts = {"node_modules", ".venv", ".cache", "bin", "obj", "dist", ".expo", "broadcast", "keystore", "keystores"}
    files = [p for p in package.rglob("*") if p.is_file()]
    for path in files:
        relative = path.relative_to(package)
        assert not any(part in blocked_parts for part in relative.parts), str(relative)
        assert not (path.name.startswith(".env") and path.name != ".env.example"), str(relative)
        assert path.suffix not in {".zip", ".rar", ".key", ".pem", ".keystore", ".pfx", ".p12"}, str(relative)
        assert not relative.as_posix().startswith(("contracts/cache/", "contracts/out/")), str(relative)
    secrets = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            name, value = line.split("=", 1)
            value = value.strip().strip("\"'")
            if any(marker in name.upper() for marker in ("PASSWORD", "KEY", "TOKEN")) and len(value) >= 8:
                secrets[name] = value.encode()
    for path in files:
        if path.suffix.lower() in {".md", ".json", ".py", ".ps1", ".cs", ".ts", ".tsx", ".toml", ".yaml", ".txt", ".sol", ".xml", ".trx"}:
            content = path.read_bytes()
            for name, value in secrets.items():
                assert value not in content, f"Secret {name} appeared in {path.relative_to(package)}"
    changes = json.loads((ROOT / "verification/subscriptions-changes.json").read_text(encoding="utf-8"))
    checked = 0
    for name in changes["created"] + changes["modified"]:
        path = ROOT / name
        if not path.is_file() or path.suffix not in {".py", ".cs", ".ts", ".tsx", ".sol", ".ps1", ".sh"}:
            continue
        text = path.read_text(encoding="utf-8-sig")
        if path.suffix == ".py":
            comments = [token.string for token in tokenize.generate_tokens(io.StringIO(text).readline) if token.type == tokenize.COMMENT]
            assert not comments, f"Source comments in {name}"
        else:
            for line in text.splitlines():
                stripped = line.strip()
                if path.suffix == ".sh" and stripped.startswith("#"):
                    assert stripped.startswith("#!"), f"Source comment in {name}"
                if stripped.startswith(("//", "/*", "* ")):
                    assert stripped.startswith(("// SPDX-License-Identifier:", "// @vitest-environment")), f"Source comment in {name}"
        checked += 1
    assert not changes["removed_original_files"], changes["removed_original_files"]
    for name, digest in manifest["hashes"].items():
        assert hashlib.sha256((package / name).read_bytes()).hexdigest() == digest, name
    size = sum(path.stat().st_size for path in files)
    assert size < 25_000_000
    result = {"submission_bytes": size, "under_25_mb": True, "manifest_hashes_verified": len(manifest["hashes"]), "forbidden_artifacts_absent": True, "local_env_secrets_absent": True, "touched_source_files_checked_for_comments": checked, "original_files_removed": 0, "archive_created": False}
    (ROOT / "verification/subscriptions-delivery-check.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
