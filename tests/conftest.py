import io
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from PIL import Image

from birdlab.domain import InferenceResult, Prediction
from birdlab.repository import Repository


@pytest.fixture
def png_bytes() -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (40, 30), "green").save(stream, "PNG")
    return stream.getvalue()


@pytest.fixture
def wav_bytes() -> bytes:
    stream = io.BytesIO()
    samples = np.sin(2 * np.pi * 440 * np.arange(22050) / 22050).astype(np.float32) * 0.2
    sf.write(stream, np.column_stack((samples, samples * 0.5)), 22050, format="WAV", subtype="PCM_16")
    return stream.getvalue()


@pytest.fixture
def repository(tmp_path: Path) -> Repository:
    return Repository(tmp_path / "birds.db", tmp_path / "uploads")


@pytest.fixture
def result() -> InferenceResult:
    return InferenceResult((Prediction("Cardinal", 0.8, "Cardinalis cardinalis"), Prediction("Blue Jay", 0.15, "Cyanocitta cristata"), Prediction("Mallard", 0.05, "Anas platyrhynchos")), "test/model", "unit-test-revision", 0.25, {"mock_used": True})


@pytest.fixture
def add_record(repository, result, png_bytes):
    from birdlab.files import save_upload, sha256

    def add(name="птах.png", kind="image", bird=None, evaluation=None):
        path = save_upload(png_bytes, name, repository.upload_dir)
        info = {"scientific_name": "Cardinalis cardinalis", "ukrainian_name": "Кардинал червоний", "family": "Cardinalidae", "habitat": "Ліси", "diet": "Насіння"} if bird is None else bird
        return repository.save(kind, name, path, sha256(png_bytes), result, info, evaluation)

    return add
