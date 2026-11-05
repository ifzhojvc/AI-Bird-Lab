import os
import uuid
from pathlib import Path

import pandas as pd

from birdlab.errors import StorageError


COLUMNS = ["image_name", "predicted_species", "confidence", "analysis_date", "description", "analysis_type", "audio_name", "audio_predicted_species", "audio_confidence", "scientific_name", "model_id", "model_revision", "analysis_id"]


def safe_cell(value: object) -> object:
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def csv_bytes(records: list[dict]) -> bytes:
    rows = []
    for r in records:
        image = r["analysis_type"] == "image"
        rows.append({"image_name": r["original_name"] if image else "", "predicted_species": r["predicted_species"] if image else "", "confidence": r["confidence"] if image else "", "analysis_date": r["analysis_date"], "description": r["description"], "analysis_type": r["analysis_type"], "audio_name": "" if image else r["original_name"], "audio_predicted_species": "" if image else r["predicted_species"], "audio_confidence": "" if image else r["confidence"], "scientific_name": r["scientific_name"] or "", "model_id": r["model_id"], "model_revision": r["model_revision"], "analysis_id": r["id"]})
    frame = pd.DataFrame(rows, columns=COLUMNS).map(safe_cell)
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8-sig")


def write_csv(records: list[dict], path: Path) -> None:
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_bytes(csv_bytes(records))
        os.replace(temporary, path)
    except OSError as exc:
        raise StorageError("Не вдалося записати CSV. Закрийте bird_analysis.csv в Excel та повторіть експорт.") from exc
    finally:
        temporary.unlink(missing_ok=True)
