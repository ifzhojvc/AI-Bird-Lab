import os
import threading
import time
from dataclasses import dataclass, field

import numpy as np
from PIL import Image

from birdlab.config import AUDIO_MODEL, AUDIO_REVISION, AUDIO_SEGMENT_SECONDS, IMAGE_MODEL, IMAGE_REVISION, MODEL_CACHE
from birdlab.domain import InferenceResult, Prediction, validate_predictions
from birdlab.errors import ModelError
from birdlab.files import AudioData
from birdlab.taxonomy import scientific_for_label


@dataclass
class ModelBundle:
    classifier: object
    sample_rate: int | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)


def _load(kind: str, offline: bool) -> ModelBundle:
    try:
        import torch
        from transformers import AutoFeatureExtractor, AutoImageProcessor, AutoModelForAudioClassification, AutoModelForImageClassification, pipeline

        torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
        model_id, revision = (IMAGE_MODEL, IMAGE_REVISION) if kind == "image" else (AUDIO_MODEL, AUDIO_REVISION)
        folder = MODEL_CACHE / f"{kind}--{revision}"
        required = ("config.json", "preprocessor_config.json", "model.safetensors")
        if not all((folder / name).is_file() for name in required):
            if offline:
                raise ModelError("Офлайн-кеш моделі відсутній або неповний. Запустіть scripts/download_models.py з інтернетом.")
            from huggingface_hub import snapshot_download

            snapshot_download(model_id, revision=revision, local_dir=str(folder), allow_patterns=list(required) + ["README.md"])
        options = {"local_files_only": True, "trust_remote_code": False}
        requested = os.getenv("BIRD_DEVICE", "auto").lower()
        if requested not in {"auto", "cpu", "cuda"}:
            raise ModelError("BIRD_DEVICE має бути auto, cpu або cuda.")
        if requested == "cuda" and not torch.cuda.is_available():
            raise ModelError("CUDA недоступна. Встановіть BIRD_DEVICE=cpu або auto.")
        device = 0 if requested != "cpu" and torch.cuda.is_available() else -1
        if kind == "image":
            processor = AutoImageProcessor.from_pretrained(folder, use_fast=False, **options)
            model = AutoModelForImageClassification.from_pretrained(folder, **options)
            if model.config.num_labels != 200 or model.classifier.out_features != 200:
                raise ModelError("Фотомодель не відповідає перевіреній конфігурації з 200 класами.")
            return ModelBundle(pipeline("image-classification", model=model.eval(), image_processor=processor, device=device))
        processor = AutoFeatureExtractor.from_pretrained(folder, **options)
        model = AutoModelForAudioClassification.from_pretrained(folder, **options)
        if model.config.num_labels != 22:
            raise ModelError("Аудіомодель має неочікуваний набір класів.")
        return ModelBundle(pipeline("audio-classification", model=model.eval(), feature_extractor=processor, device=device), int(processor.sampling_rate))
    except ModelError:
        raise
    except Exception as exc:
        mode = "Офлайн-режим увімкнено. Спочатку завантажте моделі з інтернетом." if offline else "Для першого завантаження потрібні інтернет і вільне місце. Спробуйте ще раз або запустіть scripts/download_models.py."
        raise ModelError(f"Не вдалося завантажити {'фото' if kind == 'image' else 'аудіо'}модель. {mode} ({type(exc).__name__})") from exc


class ModelCache:
    def __init__(self):
        self._models = {}
        self._lock = threading.Lock()

    def __call__(self, kind: str, offline: bool) -> ModelBundle:
        with self._lock:
            if kind not in self._models:
                self._models[kind] = _load(kind, offline)
            return self._models[kind]

    def clear(self):
        with self._lock:
            self._models.clear()

    def loaded_kinds(self):
        with self._lock:
            return sorted(self._models)


_cached_model = ModelCache()


def get_image_model(offline: bool = False) -> ModelBundle:
    return _cached_model("image", offline)


def get_audio_model(offline: bool = False) -> ModelBundle:
    return _cached_model("audio", offline)


def _predictions(raw: list[dict], kind: str) -> tuple[Prediction, ...]:
    valid = validate_predictions(raw)
    return tuple(Prediction(item["label"], item["score"], scientific_for_label(item["label"], kind)) for item in valid[:3])


def classify_image(image: Image.Image, offline: bool = False) -> InferenceResult:
    bundle = get_image_model(offline)
    started = time.perf_counter()
    try:
        with bundle.lock:
            raw = bundle.classifier(image, top_k=3)
        predictions = _predictions(raw, "image")
        return InferenceResult(predictions, IMAGE_MODEL, IMAGE_REVISION, time.perf_counter() - started, {"class_count": 200})
    except ModelError:
        raise
    except Exception as exc:
        raise ModelError("Не вдалося проаналізувати зображення. Спробуйте інший файл.") from exc


def classify_audio(audio: AudioData, offline: bool = False) -> InferenceResult:
    bundle = get_audio_model(offline)
    if audio.sample_rate != bundle.sample_rate:
        raise ModelError(f"Аудіомодель очікує {bundle.sample_rate} Гц. Перетворіть запис до цієї частоти.")
    started = time.perf_counter()
    chunk_size = AUDIO_SEGMENT_SECONDS * audio.sample_rate
    totals: dict[str, float] = {}
    sample_count = 0
    segments = 0
    try:
        for offset in range(0, len(audio.samples), chunk_size):
            segment = audio.samples[offset:offset + chunk_size]
            weight = len(segment)
            padded = np.pad(segment, (0, max(0, int(audio.sample_rate * 0.25) - weight)))
            with bundle.lock:
                raw = bundle.classifier({"raw": padded, "sampling_rate": audio.sample_rate}, top_k=22)
            valid = validate_predictions(raw, minimum=22)
            for item in valid:
                totals[item["label"]] = totals.get(item["label"], 0.0) + item["score"] * weight
            sample_count += weight
            segments += 1
        predictions = _predictions([{"label": label, "score": score / sample_count} for label, score in totals.items()], "audio")
        return InferenceResult(predictions, AUDIO_MODEL, AUDIO_REVISION, time.perf_counter() - started, {"sample_rate": audio.sample_rate, "original_rate": audio.original_rate, "original_channels": audio.original_channels, "duration": audio.duration, "segments": segments, "aggregation": "duration_weighted_mean_all_22_classes"})
    except ModelError:
        raise
    except Exception as exc:
        raise ModelError("Не вдалося проаналізувати аудіо. Спробуйте коротший або якісніший запис.") from exc
