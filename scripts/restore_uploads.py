import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def restore(root: Path = ROOT) -> int:
    mapping = root / "data" / "submission_uploads.json"
    if not mapping.exists():
        return 0
    restored = 0
    for relative, entry in json.loads(mapping.read_text(encoding="utf-8")).items():
        source = (root / entry["source"]).resolve()
        target = (root / relative).resolve()
        if not source.is_relative_to(root.resolve()) or not target.is_relative_to((root / "uploads").resolve()):
            raise RuntimeError("Небезпечний шлях у маніфесті відновлення.")
        if hashlib.sha256(source.read_bytes()).hexdigest() != entry["sha256"]:
            raise RuntimeError(f"Вихідний файл змінено: {entry['source']}")
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest() != entry["sha256"]:
                raise RuntimeError(f"Наявний файл відрізняється; перезапис заборонено: {relative}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        restored += 1
    return restored


if __name__ == "__main__":
    print(f"Відновлено копій завантажень: {restore()}")
