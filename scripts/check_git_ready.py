import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / ".test-artifacts" / "git-preparation"
PUBLIC_SETTINGS = re.compile(r"(?i)(address|decimals|chain.?id|public|username|domain|uri|enabled|mode)$")
SENSITIVE_NAME = re.compile(r"(?i)(password|passwd|secret|private.?key|api.?key|internal.?key|access.?token|refresh.?token|seed.?phrase|mnemonic)")
PRIVATE_KEY = re.compile(r"(?m)^-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----")
CRYPTO_KEY = re.compile(r'''(?i)(?:private[_ -]?key|secret[_ -]?key)\s*[=:]\s*["']?(0x[0-9a-f]{64}|[0-9a-f]{64})(?:["'\s,;}]|$)''')
SEED_PHRASE = re.compile(r'''(?i)(?:mnemonic|seed[_ -]?phrase|recovery[_ -]?phrase)\s*[=:]\s*["']([a-z]+(?:\s+[a-z]+){11,23})["']''')


def git(*args, allowed=(0,), data=None):
    result = subprocess.run(["git", *args], cwd=ROOT, input=data, capture_output=True)
    if result.returncode not in allowed:
        raise RuntimeError("Git command failed: " + " ".join(args[:2]))
    return result


def local_settings():
    blocked = {".git", ".venv", "node_modules", ".cache", ".tools", ".test-artifacts", "__pycache__", "bin", "obj", "dist", ".expo", "uploads", "storage", "backups", "verification"}
    paths = []
    for folder, directories, files in os.walk(ROOT):
        directories[:] = [name for name in directories if name not in blocked]
        for name in files:
            if (name == ".env" or name.startswith(".env.")) and not name.endswith(".example"):
                paths.append(Path(folder) / name)
    return paths


def configured_secrets(paths):
    values = []
    for path in paths:
        for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            if "=" not in line or line.lstrip().startswith("#"):
                continue
            name, value = line.split("=", 1)
            name, value = name.strip(), value.strip().strip("\"'")
            if SENSITIVE_NAME.search(name) and not PUBLIC_SETTINGS.search(name) and len(value) >= 8:
                values.append((name, value.encode("utf-8")))
    return values


def contents(staged):
    if not staged:
        names = git("ls-files", "-z", "--cached", "--others", "--exclude-standard").stdout.decode("utf-8").split("\0")
        result = {}
        for name in sorted(set(filter(None, names))):
            path = ROOT / name
            if path.is_symlink() or not path.resolve().is_relative_to(ROOT):
                raise RuntimeError("External or symbolic file requires review: " + name)
            if path.is_file():
                result[name] = path.read_bytes()
        return result
    entries = git("ls-files", "--stage", "-z").stdout.decode("utf-8").split("\0")
    mapping = {}
    for entry in filter(None, entries):
        metadata, name = entry.split("\t", 1)
        mode, object_id, stage = metadata.split()
        if stage != "0" or mode not in {"100644", "100755"}:
            raise RuntimeError("Non-regular or unresolved index entry: " + name)
        mapping[name] = object_id
    object_ids = sorted(set(mapping.values()))
    output = io.BytesIO(git("cat-file", "--batch", data=("\n".join(object_ids) + "\n").encode()).stdout)
    blobs = {}
    for object_id in object_ids:
        returned_id, kind, size = output.readline().decode("ascii").strip().split()
        assert returned_id == object_id and kind == "blob"
        blobs[object_id] = output.read(int(size))
        assert output.read(1) == b"\n"
    return {name: blobs[object_id] for name, object_id in sorted(mapping.items())}


def check(staged=False, executable=None):
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    files = contents(staged)
    assert files, "No candidate files found."
    findings = []
    if staged and git("diff", "--cached", "--check", allowed=(0, 1, 2)).returncode:
        findings.append({"file": "(index)", "rule": "git-diff-whitespace-check"})
    ignored = git("check-ignore", "--no-index", "--stdin", "-z", allowed=(0, 1), data=("\0".join(files) + "\0").encode()).stdout.decode("utf-8").split("\0")
    findings.extend({"file": name, "rule": "ignored-file-in-index"} for name in ignored if name)
    settings = local_settings()
    secrets = configured_secrets(settings)
    settings_hashes = {str(path.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest() for path in settings}
    for name, data in files.items():
        if len(data) > 100 * 1024 * 1024:
            findings.append({"file": name, "rule": "github-100-mib-limit"})
        for variable, value in secrets:
            if value in data:
                findings.append({"file": name, "rule": "local-secret-value-reused", "variable": variable})
        if b"\0" in data:
            continue
        text = data.decode("utf-8-sig", errors="replace")
        for rule, pattern in (("private-key-material", PRIVATE_KEY), ("crypto-private-key", CRYPTO_KEY), ("seed-or-recovery-phrase", SEED_PHRASE)):
            for match in pattern.finditer(text):
                findings.append({"file": name, "rule": rule, "line": text.count("\n", 0, match.start()) + 1})
        if Path(name).name == ".env.example":
            for line in text.splitlines():
                if "=" not in line or line.lstrip().startswith("#"):
                    continue
                variable, value = line.split("=", 1)
                if SENSITIVE_NAME.search(variable) and not PUBLIC_SETTINGS.search(variable) and value.strip().strip("\"'"):
                    findings.append({"file": name, "rule": "nonempty-secret-in-env-example", "variable": variable.strip()})
    snapshot = ARTIFACTS / ("scan-" + uuid4().hex)
    snapshot.mkdir()
    for name, data in files.items():
        path = snapshot / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    executable = executable or shutil.which("gitleaks") or str(ROOT / ".tools/gitleaks-8.30.1/gitleaks.exe")
    if not Path(executable).is_file():
        raise RuntimeError("Gitleaks is required. Provide --gitleaks with an installed executable.")
    scanner_report = ARTIFACTS / (snapshot.name + "-redacted.json")
    scan = subprocess.run([executable, "dir", str(snapshot), "--redact=100", "--no-banner", "--no-color", "--report-format", "json", "--report-path", str(scanner_report), "--max-decode-depth", "2"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    if scan.returncode not in {0, 1}:
        raise RuntimeError("Gitleaks failed; no secret values were printed.")
    scanner_findings = json.loads(scanner_report.read_text(encoding="utf-8")) if scanner_report.exists() else []
    if scan.returncode == 1 and not scanner_findings:
        raise RuntimeError("Gitleaks reported a failure without readable findings; the audit cannot pass.")
    for finding in scanner_findings or []:
        path = Path(finding["File"])
        name = path.relative_to(snapshot).as_posix() if path.is_absolute() else path.as_posix()
        findings.append({"file": name, "rule": finding["RuleID"], "line": finding["StartLine"]})
    for path in settings:
        name = path.relative_to(ROOT).as_posix()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == settings_hashes[name]
        assert git("check-ignore", "--quiet", "--", name, allowed=(0, 1)).returncode == 0
    sensitive_probes = [".venv/secret.txt", "web-app/node_modules/package/index.js", ".cache/huggingface/model.safetensors", "birdlab/__pycache__/config.pyc", "central-server/bin/Debug/a.dll", "central-server/obj/assets.json", "web-app/dist/index.html", "mobile-app/.expo/settings.json", "volumes/sql/data.mdf", "submission/README.md", "submission-rabbitmq/README.md", ".env.production", "web-app/.env.local", "wallets/local.json", "secrets/seed.txt", "private_key.txt", "seed_phrase.txt", "data/backups/database.bak", "birds.db", "bird_analysis.csv", "uploads/photo.jpg", "data/field_notes.json", "verification/local-deployment.json"]
    for name in sensitive_probes:
        if git("check-ignore", "--quiet", "--no-index", "--", name, allowed=(0, 1)).returncode != 0:
            findings.append({"file": name, "rule": "required-ignore-missing"})
    required = [".gitignore", ".gitattributes", ".env.example", "app.py", "birdlab/config.py", "data/birds.json", "sample_manifest.csv", "ai-server/main.py", "ai-server/worker.py", "central-server/Program.cs", "central-server/Migrations/20261103154944_CryptoSubscriptions.cs", "central-server/Models/Subscriptions.cs", "central-server.Tests/SubscriptionTests.cs", "web-app/package-lock.json", "web-app/src/App.tsx", "web-app/.env.example", "mobile-app/package-lock.json", "mobile-app/App.tsx", "mobile-app/.env.example", "contracts/foundry.toml", "contracts/src/BirdLabSubscriptions.sol", "contracts/test/BirdLabSubscriptions.t.sol", "contracts/package-lock.json", "rabbitmq/bootstrap.sh", "rabbitmq/definitions.json", "compose.yaml", "compose.local.yaml", "compose.subscriptions-test.yaml", "tests/test_worker.py"]
    for name in required:
        if name not in files:
            findings.append({"file": name, "rule": "required-source-missing"})
    remotes = git("remote").stdout.decode().splitlines()
    head = git("rev-parse", "--verify", "HEAD", allowed=(0, 128)).returncode == 0
    version = subprocess.check_output([executable, "version"], text=True, encoding="utf-8").strip()
    report = {"checkedAtUtc": datetime.now(timezone.utc).isoformat(), "mode": "staged" if staged else "candidates", "gitRoot": str(ROOT), "branch": git("branch", "--show-current").stdout.decode().strip(), "hasCommits": head, "remotes": remotes, "fileCount": len(files), "totalBytes": sum(map(len, files.values())), "largestFiles": [{"file": name, "bytes": len(data)} for name, data in sorted(files.items(), key=lambda item: len(item[1]), reverse=True)[:10]], "filesOver50MiB": [name for name, data in files.items() if len(data) > 50 * 1024 * 1024], "gitleaksVersion": version, "gitleaksFindings": len(scanner_findings or []), "localSecretVariablesChecked": len(secrets), "localEnvFilesPreservedAndIgnored": sorted(settings_hashes), "requiredIgnoreProbes": len(sensitive_probes), "requiredSources": len(required), "findings": findings, "passed": not findings, "groups": dict(sorted(Counter(name.split("/")[0] if "/" in name else "(root)" for name in files).items())), "files": [{"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()} for name, data in files.items()]}
    (ARTIFACTS / ("staged-report.json" if staged else "candidate-report.json")).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (ARTIFACTS / ("staged-files.txt" if staged else "candidate-files.txt")).write_text("\n".join(files) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("mode", "fileCount", "totalBytes", "largestFiles", "filesOver50MiB", "gitleaksVersion", "gitleaksFindings", "localSecretVariablesChecked", "localEnvFilesPreservedAndIgnored", "findings", "passed", "groups")}, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Локальна перевірка Git-файлів, секретів і розміру без commit/push та без виведення значень секретів.")
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--gitleaks")
    args = parser.parse_args()
    raise SystemExit(0 if check(args.staged, args.gitleaks)["passed"] else 1)
