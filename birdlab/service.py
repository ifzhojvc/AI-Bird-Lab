import csv
from pathlib import Path
from typing import Callable

from birdlab.config import AUDIO_MODEL, AUDIO_REVISION, CSV_PATH, MANIFEST_PATH, SAMPLE_DIR
from birdlab.errors import BirdLabError, InputError, StorageError
from birdlab.export import write_csv
from birdlab.files import load_audio, load_image, read_file, save_upload, sha256
from birdlab.models import classify_audio, classify_image, get_audio_model
from birdlab.reference import bird_reference
from birdlab.repository import Repository


def sample_manifest() -> list[dict]:
    if not MANIFEST_PATH.exists():
        return []
    with MANIFEST_PATH.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def verified_evaluation(row: dict, content: bytes) -> dict:
    if row.get("label_verified") != "true" or row.get("sha256") != sha256(content) or not row.get("label_source") or not row.get("scientific_name"):
        raise InputError("Еталонна мітка або SHA-256 зразка не підтверджені. Оцінювання скасовано.")
    from birdlab.taxonomy import scientific_for_label

    if scientific_for_label(row["model_label"], "image") != row["scientific_name"]:
        raise InputError("Еталонна мітка не відповідає перевіреному довіднику.")
    return {"expected_label": row["model_label"], "expected_scientific": row["scientific_name"], "label_source": row["label_source"], "file_hash": sha256(content)}


class AnalysisService:
    def __init__(self, repository: Repository, offline: bool = False, online_reference: bool = False, export_path: Path = CSV_PATH):
        self.repository = repository
        self.offline = offline
        self.online_reference = online_reference and not offline
        self.export_path = export_path
        self.last_warning: str | None = None

    def analyze(self, data: bytes, name: str, kind: str, evaluation: dict | None = None) -> int:
        self.last_warning = None
        if kind == "image":
            media = load_image(data, name)
            result = classify_image(media, self.offline)
        elif kind == "audio":
            from birdlab.config import MAX_AUDIO_BYTES
            from birdlab.files import validate_size

            validate_size(data, MAX_AUDIO_BYTES)
            media = load_audio(data, name)
            expected_rate = get_audio_model(self.offline).sample_rate
            if media.sample_rate != expected_rate:
                media = load_audio(data, name, target_rate=expected_rate)
            result = classify_audio(media, self.offline)
        else:
            raise InputError("Невідомий тип аналізу.")
        bird = bird_reference(result.predictions[0].label, kind, self.online_reference)
        path = save_upload(data, name, self.repository.upload_dir)
        try:
            analysis_id = self.repository.save(kind, name, path, sha256(data), result, bird, evaluation)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        self.refresh_export()
        return analysis_id

    def refresh_export(self) -> None:
        try:
            write_csv(self.repository.all(), self.export_path)
        except StorageError as exc:
            self.last_warning = "Зміни в базі збережено. " + str(exc)

    def batch(self, files: list[tuple[str, bytes, dict | None]], progress: Callable | None = None) -> list[dict]:
        results = []
        for index, (name, content, evaluation) in enumerate(files):
            try:
                analysis_id = self.analyze(content, name, "image", evaluation)
                row = {"file": name, "id": analysis_id, "status": "Збережено", "warning": self.last_warning or ""}
            except BirdLabError as exc:
                row = {"file": name, "id": None, "status": str(exc), "warning": ""}
            results.append(row)
            if progress:
                progress((index + 1) / len(files), name)
        return results

    def batch_samples(self, progress: Callable | None = None) -> list[dict]:
        rows = sample_manifest()
        results = []
        for index, row in enumerate(rows):
            name = row["file_name"]
            try:
                path = (SAMPLE_DIR / name).resolve()
                if not path.is_relative_to(SAMPLE_DIR.resolve()):
                    raise InputError("Некоректний шлях у маніфесті.")
                data = read_file(path)
                evaluation = verified_evaluation(row, data)
                result = self.batch([(name, data, evaluation)])[0]
            except BirdLabError as exc:
                result = {"file": name, "id": None, "status": str(exc), "warning": ""}
            results.append(result)
            if progress:
                progress((index + 1) / len(rows), name)
        return results
