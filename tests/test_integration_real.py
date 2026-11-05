import os

import pytest

from birdlab.config import ROOT, SAMPLE_DIR
from birdlab.files import read_file
from birdlab.service import AnalysisService, sample_manifest, verified_evaluation


pytestmark = [pytest.mark.integration, pytest.mark.skipif(os.environ.get("RUN_REAL_MODELS") != "1", reason="Справжні моделі запускаються окремо: RUN_REAL_MODELS=1")]


def test_real_image_pipeline_database_csv(repository, tmp_path):
    rows = sample_manifest()
    assert rows, "Спочатку завантажте реальні фотографії"
    row = rows[0]
    data = read_file(SAMPLE_DIR / row["file_name"])
    service = AnalysisService(repository, offline=True, export_path=tmp_path / "real.csv")
    analysis_id = service.analyze(data, row["file_name"], "image", verified_evaluation(row, data))
    record = repository.get(analysis_id)
    assert record["model_id"] == "PwNzDust/vit_cub"
    assert len(record["predictions"]) == 3
    assert all(0 <= prediction["score"] <= 1 for prediction in record["predictions"])
    assert record["metadata"].get("mock_used", False) is False
    assert len(repository.evaluations()) == 1
    assert service.export_path.read_bytes().startswith(b"\xef\xbb\xbf")


def test_real_audio_pipeline(repository, tmp_path):
    path = ROOT / "sample_audio" / "robin.wav"
    assert path.is_file(), "Спочатку завантажте справжній аудіозразок"
    service = AnalysisService(repository, offline=True, export_path=tmp_path / "real.csv")
    analysis_id = service.analyze(read_file(path), path.name, "audio")
    record = repository.get(analysis_id)
    assert record["model_id"] == "greenarcade/wav2vec2-vd-bird-sound-classification"
    assert len(record["predictions"]) == 3 and record["metadata"]["sample_rate"] == 16000
    assert repository.evaluations() == []
