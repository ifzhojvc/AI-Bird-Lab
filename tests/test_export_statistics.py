import csv
import io

import pytest

from birdlab.config import UNKNOWN
from birdlab.export import COLUMNS, csv_bytes, write_csv
from birdlab.statistics import build_charts, filter_gallery, quality_metrics, summarize


def decode(content):
    return list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))


def test_empty_csv():
    content = csv_bytes([])
    assert content.startswith(b"\xef\xbb\xbf") and decode(content) == []
    assert next(csv.reader(io.StringIO(content.decode("utf-8-sig")))) == COLUMNS


def test_csv_images_and_audio(repository, add_record, tmp_path):
    add_record(name='птах,"1".png')
    add_record(name="спів.wav", kind="audio")
    rows = decode(csv_bytes(repository.all(descending=False)))
    assert rows[0]["image_name"] == 'птах,"1".png'
    assert rows[0]["audio_name"] == "" and rows[0]["confidence"] == "0.8"
    assert rows[1]["image_name"] == rows[1]["predicted_species"] == rows[1]["confidence"] == ""
    assert rows[1]["audio_name"] == "спів.wav" and rows[1]["audio_confidence"] == "0.8"
    path = tmp_path / "bird_analysis.csv"
    write_csv(repository.all(), path)
    assert len(decode(path.read_bytes())) == 2


def test_csv_formula_escape(repository, add_record):
    add_record(name="=HYPERLINK.png")
    assert decode(csv_bytes(repository.all()))[0]["image_name"].startswith("'=")


def test_empty_statistics():
    summary = summarize([])
    assert summary["images"] == summary["audio"] == summary["unique_species"] == 0
    assert summary["average_confidence"] is summary["max_record"] is None
    assert build_charts([]) == {} and quality_metrics([]) == []


def test_statistics_and_five_charts(repository, add_record):
    add_record()
    add_record(kind="audio", name="song.wav")
    summary = summarize(repository.all())
    assert summary["images"] == summary["audio"] == summary["unique_species"] == 1
    assert summary["average_confidence"] == pytest.approx(0.8)
    assert summary["species_counts"] == {"Cardinal": 2}
    charts = build_charts(repository.all())
    assert len(charts) == 5
    assert all(chart.to_json() for chart in charts.values())


def test_gallery_handles_missing_reference(repository, add_record):
    add_record()
    add_record(bird={})
    rows = repository.all()
    assert len(filter_gallery(rows)) == 2
    assert len(filter_gallery(rows, family="Cardinalidae", habitat="Ліси", diet="Насіння")) == 1
    assert len(filter_gallery(rows, family=UNKNOWN)) == 1
    assert filter_gallery(rows, family="Missing") == []


def test_quality_is_labelled_and_grouped():
    rows = [{"model_id": "a", "model_revision": "r", "experiment": "original", "top1_correct": 1, "top3_correct": 1}, {"model_id": "a", "model_revision": "r", "experiment": "original", "top1_correct": 0, "top3_correct": 1}]
    quality = quality_metrics(rows)[0]
    assert quality["count"] == 2 and quality["incorrect"] == 1
    assert quality["top1_accuracy"] == 0.5 and quality["top3_accuracy"] == 1


def test_repeated_photo_does_not_inflate_quality_sample():
    row = {"model_id": "a", "model_revision": "r", "experiment": "original", "file_hash": "same-photo", "top1_correct": 1, "top3_correct": 1}
    assert quality_metrics([row, row])[0]["count"] == 1
