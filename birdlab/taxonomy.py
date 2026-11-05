import json
from functools import lru_cache
from pathlib import Path

from birdlab.config import CATALOG_PATH


@lru_cache(maxsize=4)
def load_catalog(path: Path = CATALOG_PATH) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_label(label: str, model_type: str) -> dict | None:
    for bird in load_catalog().values():
        if label in bird.get(f"{model_type}_labels", []):
            return dict(bird)
    return None


def scientific_for_label(label: str, model_type: str) -> str | None:
    bird = resolve_label(label, model_type)
    return bird.get("scientific_name") if bird else None


def compare_taxa(first: str | None, second: str | None) -> str:
    if not first or not second:
        return "Порівняння неможливе через відсутність надійного зіставлення"
    if first == second:
        return "Моделі визначили той самий вид"
    return "Моделі визначили різні види"
