import hashlib
import json

import pytest

from scripts.restore_uploads import restore


def make_fixture(root, target="uploads/original.jpg"):
    (root / "sample_images").mkdir()
    (root / "data").mkdir()
    source = root / "sample_images" / "bird.jpg"
    source.write_bytes(b"immutable-bird-image")
    mapping = {target: {"source": "sample_images/bird.jpg", "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}}
    (root / "data" / "submission_uploads.json").write_text(json.dumps(mapping), encoding="utf-8")


def test_exact_duplicate_restoration_and_second_run(tmp_path):
    make_fixture(tmp_path)
    assert restore(tmp_path) == 1
    assert (tmp_path / "uploads" / "original.jpg").read_bytes() == (tmp_path / "sample_images" / "bird.jpg").read_bytes()
    assert restore(tmp_path) == 0


def test_modified_existing_upload_is_never_overwritten(tmp_path):
    make_fixture(tmp_path)
    (tmp_path / "uploads").mkdir()
    target = tmp_path / "uploads" / "original.jpg"
    target.write_bytes(b"user-modified-content")
    with pytest.raises(RuntimeError, match="перезапис заборонено"):
        restore(tmp_path)
    assert target.read_bytes() == b"user-modified-content"


def test_restore_rejects_target_outside_uploads(tmp_path):
    make_fixture(tmp_path, "../../escape.jpg")
    with pytest.raises(RuntimeError, match="Небезпечний"):
        restore(tmp_path)
