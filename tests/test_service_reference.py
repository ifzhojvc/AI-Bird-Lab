from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from birdlab.errors import ModelError, StorageError
from birdlab.files import sha256
from birdlab.reference import bird_reference
from birdlab.service import AnalysisService, verified_evaluation


def test_service_saves_once_on_explicit_call(repository, result, png_bytes, tmp_path, monkeypatch):
    classifier = Mock(return_value=result)
    monkeypatch.setattr("birdlab.service.classify_image", classifier)
    service = AnalysisService(repository, export_path=tmp_path / "bird_analysis.csv")
    analysis_id = service.analyze(png_bytes, "птах.png", "image")
    assert len(repository.all()) == classifier.call_count == 1
    assert repository.get(analysis_id) is not None
    assert service.export_path.exists()


def test_failed_model_never_saves_fake_result(repository, png_bytes, monkeypatch, tmp_path):
    monkeypatch.setattr("birdlab.service.classify_image", Mock(side_effect=ModelError("Помилка моделі")))
    service = AnalysisService(repository, export_path=tmp_path / "out.csv")
    with pytest.raises(ModelError):
        service.analyze(png_bytes, "bird.png", "image")
    assert repository.all() == [] and list(repository.upload_dir.iterdir()) == []


def test_failed_database_removes_new_file(repository, png_bytes, result, monkeypatch, tmp_path):
    monkeypatch.setattr("birdlab.service.classify_image", Mock(return_value=result))
    monkeypatch.setattr(repository, "save", Mock(side_effect=StorageError("Помилка БД")))
    service = AnalysisService(repository, export_path=tmp_path / "out.csv")
    with pytest.raises(StorageError):
        service.analyze(png_bytes, "bird.png", "image")
    assert list(repository.upload_dir.iterdir()) == []


def test_batch_continues_after_bad_file(repository, png_bytes, result, monkeypatch, tmp_path):
    monkeypatch.setattr("birdlab.service.classify_image", Mock(return_value=result))
    service = AnalysisService(repository, export_path=tmp_path / "out.csv")
    progress = Mock()
    rows = service.batch([("first.png", png_bytes, None), ("bad.png", b"broken", None), ("last.png", png_bytes, None)], progress)
    assert [row["id"] is not None for row in rows] == [True, False, True]
    assert progress.call_count == 3 and len(repository.all()) == 2


def test_export_failure_reports_saved_analysis(repository, png_bytes, result, monkeypatch, tmp_path):
    monkeypatch.setattr("birdlab.service.classify_image", Mock(return_value=result))
    monkeypatch.setattr("birdlab.service.write_csv", Mock(side_effect=StorageError("CSV зайнято")))
    service = AnalysisService(repository, export_path=tmp_path / "out.csv")
    analysis_id = service.analyze(png_bytes, "bird.png", "image")
    assert repository.get(analysis_id) and "збережено" in service.last_warning


def test_api_failure_retains_verified_local_data(monkeypatch):
    bird_reference.clear()
    monkeypatch.setattr("birdlab.reference.requests.get", Mock(side_effect=requests.ConnectionError()))
    bird = bird_reference("Cardinal", "image", True)
    assert bird["scientific_name"] == "Cardinalis cardinalis"
    assert "недоступний" in bird["reference_status"]
    bird_reference.clear()


def test_api_fuzzy_match_is_not_used(monkeypatch):
    bird_reference.clear()
    response = Mock()
    response.json.return_value = {"matchType": "FUZZY", "canonicalName": "Other taxon", "family": "Wrong family"}
    monkeypatch.setattr("birdlab.reference.requests.get", Mock(return_value=response))
    bird = bird_reference("Cardinal", "image", True)
    assert bird["family"] == "Cardinalidae" and "не підтвердив" in bird["reference_status"]
    bird_reference.clear()


def test_no_reference_never_guesses():
    assert "scientific_name" not in bird_reference("Completely unknown class", "image")


def test_sample_hash_and_mapping_validation(png_bytes):
    row = {"label_verified": "true", "sha256": sha256(png_bytes), "label_source": "https://example.org/verified", "scientific_name": "Cardinalis cardinalis", "model_label": "Cardinal"}
    assert verified_evaluation(row, png_bytes)["expected_label"] == "Cardinal"
    row["sha256"] = "changed"
    from birdlab.errors import InputError

    with pytest.raises(InputError, match="SHA-256"):
        verified_evaluation(row, png_bytes)
