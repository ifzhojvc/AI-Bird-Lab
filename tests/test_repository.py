import sqlite3

import pytest

from birdlab.errors import StorageError
from birdlab.files import sha256


def test_creates_database_and_tables(repository):
    assert repository.db_path.is_file()
    with repository.connection() as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"analyses", "predictions", "bird_info", "evaluations"} <= tables


def test_empty_history(repository):
    assert repository.all() == [] and repository.get(999) is None
    assert repository.evaluations() == [] and repository.clear() == 0


def test_saves_three_predictions(repository, add_record):
    analysis_id = add_record()
    record = repository.get(analysis_id)
    assert record["original_name"] == "птах.png"
    assert record["model_id"] == "test/model"
    assert record["confidence"] == 0.8 and record["scientific_name"] == "Cardinalis cardinalis"
    assert len(record["predictions"]) == 3
    assert [p["rank"] for p in record["predictions"]] == [1, 2, 3]
    assert record["metadata"]["mock_used"] is True
    assert repository.media_path(record).is_file()


@pytest.mark.parametrize("query", ["cardinal", "CARDINAL", "Кардинал", "ЧЕРВОНИЙ", "Cardinalis cardinalis"])
def test_search_unicode_and_english(repository, add_record, query):
    add_record()
    assert len(repository.all(query)) == 1


def test_sql_input_is_data(repository, add_record):
    add_record(name="' OR 1=1; --.png")
    assert repository.all("' OR 1=1") == []
    assert len(repository.all()) == 1


def test_filter_and_sort(repository, add_record):
    first = add_record()
    second = add_record(name="second.wav", kind="audio")
    assert [r["id"] for r in repository.all(descending=False)] == [first, second]
    assert [r["id"] for r in repository.all(kind="audio")] == [second]


def test_delete_cascades_and_preserves_other_files(repository, add_record, tmp_path):
    first = add_record()
    second = add_record()
    original = tmp_path / "original.png"
    original.write_bytes(b"do not delete")
    first_path = repository.media_path(repository.get(first))
    assert repository.delete(first) is True
    assert not first_path.exists() and original.exists()
    assert repository.get(second) is not None
    with repository.connection() as connection:
        assert connection.execute("SELECT count(*) FROM predictions WHERE analysis_id=?", (first,)).fetchone()[0] == 0
    assert repository.delete(first) is False


def test_delete_missing_media(repository, add_record):
    analysis_id = add_record()
    repository.media_path(repository.get(analysis_id)).unlink()
    assert repository.delete(analysis_id)


def test_clear_history(repository, add_record):
    add_record()
    add_record()
    assert repository.clear() == 2 and not repository.all()
    assert list(repository.upload_dir.iterdir()) == []


def test_refuses_outside_path(repository, tmp_path):
    with pytest.raises(StorageError, match="межі"):
        repository.media_path({"file_path": "../outside.jpg"})


def test_evaluation_and_delete(repository, add_record, png_bytes):
    evaluation = {"expected_label": "Cardinal", "expected_scientific": "Cardinalis cardinalis", "label_source": "https://example.org/label", "file_hash": sha256(png_bytes)}
    analysis_id = add_record(evaluation=evaluation)
    row = repository.evaluations()[0]
    assert row["top1_correct"] == row["top3_correct"] == 1
    assert repository.get(analysis_id)["evaluation"]["expected_label"] == "Cardinal"
    repository.delete(analysis_id)
    assert repository.evaluations() == []


def test_invalid_evaluation_rolls_back(repository, add_record):
    with pytest.raises(StorageError, match="мітки"):
        add_record(evaluation={"label_source": "", "file_hash": "no"})
    assert repository.all() == []


def test_database_failure_is_readable(tmp_path):
    from birdlab.repository import Repository

    path = tmp_path / "broken.db"
    path.write_bytes(b"not a database")
    with pytest.raises(StorageError, match="бази даних"):
        Repository(path, tmp_path / "uploads")
