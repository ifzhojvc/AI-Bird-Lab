import math
from dataclasses import asdict, dataclass, field
from typing import Any

from birdlab.errors import ModelError


@dataclass(frozen=True)
class Prediction:
    label: str
    score: float
    scientific_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class InferenceResult:
    predictions: tuple[Prediction, ...]
    model_id: str
    revision: str
    elapsed_seconds: float
    metadata: dict[str, Any] = field(default_factory=dict)


def validate_predictions(raw: list[dict], minimum: int = 3) -> list[dict]:
    if not isinstance(raw, list) or len(raw) < minimum:
        raise ModelError("Модель повернула порожню або неповну відповідь. Результат не збережено.")
    output = []
    for item in raw:
        try:
            label = item["label"]
            score = float(item["score"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ModelError("Некоректний формат відповіді моделі.") from exc
        if not isinstance(label, str) or not label.strip() or not math.isfinite(score) or not 0 <= score <= 1:
            raise ModelError("Модель повернула некоректну назву або confidence.")
        output.append({"label": label, "score": score})
    if len({item["label"] for item in output}) != len(output):
        raise ModelError("Модель повернула повторювані класи.")
    return sorted(output, key=lambda item: item["score"], reverse=True)
