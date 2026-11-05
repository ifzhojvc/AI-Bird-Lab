import threading
from unittest.mock import Mock

import numpy as np
import pytest

from birdlab.domain import validate_predictions
from birdlab.errors import ModelError
from birdlab.files import AudioData
from birdlab.models import ModelBundle, classify_audio, classify_image
from birdlab.taxonomy import compare_taxa, scientific_for_label


@pytest.mark.parametrize("raw", [[], None, [{"label": "a", "score": 0.2}], [{"label": "a", "score": float("nan")}] * 3, [{"label": "a", "score": 1.5}] * 3, [{"label": "a", "score": 0.3}] * 3])
def test_bad_predictions(raw):
    with pytest.raises(ModelError):
        validate_predictions(raw)


def test_top_three_sorted_and_mapped(monkeypatch):
    classifier = Mock(return_value=[{"label": "Mallard", "score": 0.1}, {"label": "Blue Jay", "score": 0.2}, {"label": "Cardinal", "score": 0.7}])
    monkeypatch.setattr("birdlab.models.get_image_model", lambda offline: ModelBundle(classifier))
    result = classify_image(Mock(), True)
    assert result.predictions[0].label == "Cardinal"
    assert result.predictions[0].scientific_name == "Cardinalis cardinalis"
    assert len(result.predictions) == 3


def test_empty_real_dependency_response_is_error(monkeypatch):
    monkeypatch.setattr("birdlab.models.get_image_model", lambda offline: ModelBundle(Mock(return_value=[])))
    with pytest.raises(ModelError, match="неповну"):
        classify_image(Mock())


def test_audio_duration_weighted_all_classes(monkeypatch):
    labels = ["background", "Great_egret"] + [f"class_{i}" for i in range(20)]
    first = [{"label": label, "score": 0.6 if index == 0 else 0.4 if index == 1 else 0} for index, label in enumerate(labels)]
    second = [{"label": label, "score": 0.0 if index == 0 else 1.0 if index == 1 else 0} for index, label in enumerate(labels)]
    classifier = Mock(side_effect=[first, second])
    monkeypatch.setattr("birdlab.models.get_audio_model", lambda offline: ModelBundle(classifier, 16000))
    audio = AudioData(np.ones(6 * 16000, dtype=np.float32), 16000, 6, 16000, 1)
    result = classify_audio(audio)
    assert result.metadata["segments"] == 2
    assert classifier.call_args_list[0].kwargs["top_k"] == 22
    assert result.predictions[0].label == "background"
    assert result.predictions[0].score == pytest.approx(0.5)
    assert result.predictions[1].score == pytest.approx(0.5)


def test_audio_wrong_sample_rate(monkeypatch):
    monkeypatch.setattr("birdlab.models.get_audio_model", lambda offline: ModelBundle(Mock(), 16000))
    with pytest.raises(ModelError, match="16000"):
        classify_audio(AudioData(np.ones(8000), 8000, 1, 8000, 1))


@pytest.mark.parametrize("first,second,expected", [("Halcyon smyrnensis", "Halcyon smyrnensis", "той самий"), ("Anas acuta", "Anas platyrhynchos", "різні"), (None, "Anas acuta", "неможливе"), (None, None, "неможливе")])
def test_taxonomic_comparison(first, second, expected):
    assert expected in compare_taxa(first, second)


@pytest.mark.parametrize("label", ["White_Ibis", "Golden_oriole", "background", "unknown", "Great egret"])
def test_no_fuzzy_or_ambiguous_mapping(label):
    assert scientific_for_label(label, "audio") is None


def test_verified_overlap_across_models():
    assert scientific_for_label("White breasted Kingfisher", "image") == scientific_for_label("White-throated_kingfisher", "audio") == "Halcyon smyrnensis"


def test_cold_offline_error(monkeypatch, tmp_path):
    from birdlab.models import _load

    monkeypatch.setattr("birdlab.models.MODEL_CACHE", tmp_path)
    with pytest.raises(ModelError, match="Офлайн-кеш"):
        _load("image", True)


def test_warm_model_is_shared_when_offline_toggle_changes(monkeypatch):
    from birdlab.models import _cached_model, get_image_model

    _cached_model.clear()
    loader = Mock(return_value=ModelBundle(Mock()))
    monkeypatch.setattr("birdlab.models._load", loader)
    try:
        assert get_image_model(False) is get_image_model(True)
        assert loader.call_count == 1
    finally:
        _cached_model.clear()
