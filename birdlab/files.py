import hashlib
import io
import uuid
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageOps, UnidentifiedImageError

from birdlab.config import MAX_AUDIO_BYTES, MAX_AUDIO_SECONDS, MAX_IMAGE_BYTES, MAX_IMAGE_PIXELS
from birdlab.errors import InputError, StorageError


@dataclass(frozen=True)
class AudioData:
    samples: np.ndarray
    sample_rate: int
    duration: float
    original_rate: int
    original_channels: int


def read_file(path: Path) -> bytes:
    try:
        if path.stat().st_size > MAX_AUDIO_BYTES:
            raise InputError("Файл завеликий. Максимальний розмір — 50 МБ.")
        return path.read_bytes()
    except OSError as exc:
        raise InputError("Не вдалося прочитати файл. Перевірте шлях і права доступу.") from exc


def validate_size(data: bytes, limit: int) -> None:
    if not data:
        raise InputError("Файл порожній. Виберіть інший файл.")
    if len(data) > limit:
        raise InputError(f"Файл завеликий. Дозволено до {limit // (1024 * 1024)} МБ.")


def load_image(data: bytes, name: str) -> Image.Image:
    validate_size(data, MAX_IMAGE_BYTES)
    suffix = Path(name).suffix.lower()
    formats = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG"}
    if suffix not in formats:
        raise InputError("Підтримуються лише зображення JPG, JPEG та PNG.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as probe:
                if probe.format != formats[suffix]:
                    raise InputError("Вміст зображення не відповідає розширенню файлу.")
                if probe.width * probe.height > MAX_IMAGE_PIXELS:
                    raise InputError("Зображення завелике: дозволено до 25 мільйонів пікселів.")
                probe.verify()
            with Image.open(io.BytesIO(data)) as original:
                image = ImageOps.exif_transpose(original)
                if image.mode in ("RGBA", "LA") or "transparency" in image.info:
                    rgba = image.convert("RGBA")
                    background = Image.new("RGBA", rgba.size, "white")
                    image = Image.alpha_composite(background, rgba)
                return image.convert("RGB").copy()
    except InputError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise InputError("Зображення пошкоджене або має небезпечний розмір. Виберіть коректне JPG/PNG.") from exc


def load_audio(data: bytes, name: str, target_rate: int = 16000) -> AudioData:
    validate_size(data, MAX_AUDIO_BYTES)
    expected = {".wav": {"WAV", "WAVEX", "RF64"}, ".flac": {"FLAC"}, ".mp3": {"MP3", "MPEG"}}
    suffix = Path(name).suffix.lower()
    if suffix not in expected:
        raise InputError("Підтримуються WAV, FLAC та MP3.")
    try:
        with sf.SoundFile(io.BytesIO(data)) as audio:
            if audio.format not in expected[suffix]:
                raise InputError("Вміст аудіо не відповідає розширенню файлу.")
            rate, channels, frames = audio.samplerate, audio.channels, len(audio)
            duration = frames / rate
            if not 0.25 <= duration <= MAX_AUDIO_SECONDS:
                raise InputError("Тривалість запису має бути від 0,25 до 60 секунд. Обріжте довший запис.")
            if channels > 8 or rate > 192000:
                raise InputError("Дозволено до 8 каналів та частоту до 192 кГц.")
            samples = audio.read(dtype="float32", always_2d=True).mean(axis=1)
        if not np.isfinite(samples).all() or float(np.max(np.abs(samples))) < 1e-7:
            raise InputError("Аудіозапис містить тишу або некоректні значення.")
        if rate != target_rate:
            import librosa

            samples = librosa.resample(samples, orig_sr=rate, target_sr=target_rate)
        return AudioData(np.ascontiguousarray(samples, dtype=np.float32), target_rate, duration, rate, channels)
    except InputError:
        raise
    except (RuntimeError, OSError, ValueError, sf.LibsndfileError) as exc:
        raise InputError("Не вдалося прочитати аудіо. Перевірте файл; для несумісного MP3 використайте WAV.") from exc


def save_upload(data: bytes, name: str, directory: Path) -> Path:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{uuid.uuid4().hex}{Path(name).suffix.lower()}"
        path.write_bytes(data)
        return path
    except OSError as exc:
        raise StorageError("Не вдалося зберегти завантажений файл. Перевірте вільне місце та права доступу.") from exc


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
