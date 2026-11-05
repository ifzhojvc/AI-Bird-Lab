import secrets
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    target = ROOT / ".env"
    text = target.read_text(encoding="utf-8-sig") if target.exists() else ""
    values = {
        "MSSQL_SA_PASSWORD": lambda: "Bird!9" + secrets.token_hex(20),
        "AI_INTERNAL_KEY": lambda: secrets.token_hex(32),
        "RABBITMQ_USERNAME": lambda: "birdlab",
        "RABBITMQ_PASSWORD": lambda: secrets.token_hex(32),
    }
    lines = text.splitlines()
    changed = []
    for name, create in values.items():
        index = next((i for i, line in enumerate(lines) if line.startswith(name + "=")), None)
        if index is None:
            lines.append(f"{name}={create()}")
            changed.append(name)
        elif not lines[index].split("=", 1)[1].strip().strip("\"'"):
            lines[index] = f"{name}={create()}"
            changed.append(name)
    if changed:
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Налаштовано: " + (", ".join(changed) if changed else "усі потрібні змінні вже задано") + ". Значення секретів не виводяться.")


if __name__ == "__main__":
    main()
