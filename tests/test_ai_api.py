import io
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ai-server"))

from ai_api.app import app
from birdlab.errors import ModelError


@pytest.fixture
def client():
    return TestClient(app)


def test_health_does_not_load_model(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert isinstance(response.json()["models_cached"], list)


@pytest.mark.parametrize("name,content", [("fake.png", b"not a PNG"), ("bird.exe", b"MZ"), ("empty.jpg", b"")])
def test_image_rejects_invalid_uploads(client, name, content):
    response = client.post("/predict/image", files={"file": (name, content)})
    assert response.status_code == 422
    assert set(response.json()) == {"code", "message", "request_id"}


def test_corrupt_audio_is_not_classified(client):
    response = client.post("/predict/audio", files={"file": ("broken.wav", b"RIFFbroken")})
    assert response.status_code == 422


def test_missing_multipart_is_structured(client):
    response = client.post("/predict/image")
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_internal_key_protects_inference_and_health(client, monkeypatch):
    monkeypatch.setenv("AI_INTERNAL_KEY", "unit-test-key")
    assert client.get("/health").status_code == 401
    assert client.get("/health", headers={"X-AI-Key": "unit-test-key"}).status_code == 200


def test_model_failure_is_not_a_prediction(client, png_bytes, monkeypatch):
    def unavailable(*args):
        raise ModelError("Офлайн-кеш відсутній")
    monkeypatch.setattr("ai_api.app.classify_image", unavailable)
    response = client.post("/predict/image", files={"file": ("bird.png", png_bytes)})
    assert response.status_code == 503
    assert response.json()["code"] == "model_unavailable"
    assert "predictions" not in response.json()


def test_contract_maps_original_predictions(client, png_bytes, result, monkeypatch):
    monkeypatch.setattr("ai_api.app.classify_image", lambda *args: result)
    payload = client.post("/predict/image", files={"file": ("bird.png", png_bytes)}).json()
    assert payload["model_id"] == "test/model"
    assert [p["rank"] for p in payload["predictions"]] == [1, 2, 3]
    assert payload["predictions"][0]["scientific_name"] == "Cardinalis cardinalis"


def test_file_size_limit(client, monkeypatch):
    monkeypatch.setattr("ai_api.app.MAX_IMAGE_BYTES", 8)
    assert client.post("/predict/image", files={"file": ("large.jpg", b"123456789")}).status_code == 413


@pytest.mark.integration
@pytest.mark.skipif(__import__("os").environ.get("RUN_REAL_MODELS") != "1", reason="RUN_REAL_MODELS=1 required")
def test_real_fastapi_image_and_audio(client):
    root = Path(__file__).resolve().parents[1]
    for kind, path in [("image", root / "sample_images" / "01_Cardinalis_cardinalis.jpg"), ("audio", root / "sample_audio" / "robin.wav")]:
        response = client.post(f"/predict/{kind}", files={"file": (path.name, path.read_bytes())})
        assert response.status_code == 200, response.text
        payload = response.json()
        assert len(payload["predictions"]) == 3
        assert payload["metadata"]["mock_used"] is False
        assert all(0 <= p["confidence"] <= 1 for p in payload["predictions"])
