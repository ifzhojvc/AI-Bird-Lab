import argparse
import json
import re
import subprocess
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]


def environment():
    values = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            name, value = line.split("=", 1)
            values[name.strip()] = value.strip().strip("\"'")
    return values


def session():
    env = environment()
    client = requests.Session()
    client.auth = (env["RABBITMQ_USERNAME"], env["RABBITMQ_PASSWORD"])
    return client


def snapshot(client=None):
    client = client or session()
    def get(path):
        result = client.get("http://127.0.0.1:15672/api" + path, timeout=10)
        result.raise_for_status()
        return result.json()
    overview = get("/overview")
    queues = get("/queues/birdlab")
    return {"rabbitmq_version": overview["rabbitmq_version"], "queues": [{key: q.get(key) for key in ("name", "type", "durable", "messages", "messages_ready", "messages_unacknowledged", "consumers", "policy", "message_stats")} for q in queues], "policies": get("/policies/birdlab")}


def compose(*args, timeout=180):
    result = subprocess.run(["docker", "compose", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    output = result.stdout + result.stderr
    for name, value in environment().items():
        if value and ("PASSWORD" in name or "KEY" in name):
            output = output.replace(value, "[REDACTED]")
    output = re.sub(r"(add_user\s+\S+\s+)\S+", r"\1[REDACTED]", output)
    if result.returncode:
        raise RuntimeError(output[-6000:])
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Перегляд RabbitMQ без виведення секретів.")
    parser.add_argument("command", choices=["queues", "logs"])
    args = parser.parse_args()
    if args.command == "queues":
        print(json.dumps(snapshot(), ensure_ascii=False, indent=2))
    else:
        print(compose("logs", "--tail", "50", "central", "worker", "rabbitmq", "ai"))
