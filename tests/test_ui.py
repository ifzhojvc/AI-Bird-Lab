from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from birdlab.config import ROOT
from birdlab.ui.common import PAGES


@pytest.fixture
def app_test(tmp_path, monkeypatch):
    monkeypatch.setattr("birdlab.config.DB_PATH", tmp_path / "birds.db")
    monkeypatch.setattr("birdlab.config.UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr("birdlab.config.CSV_PATH", tmp_path / "out.csv")
    monkeypatch.setattr("birdlab.models._load", Mock(side_effect=AssertionError("Navigation must not load models")))
    return AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)


@pytest.mark.parametrize("page", PAGES)
def test_all_eight_pages_without_model_loading(app_test, page):
    app_test.run()
    app_test.sidebar.radio[0].set_value(page).run()
    assert len(app_test.exception) == 0
    assert len(app_test.error) == 0


def test_home_navigation_is_functional(app_test):
    app_test.run()
    app_test.button(key="home_Аналіз фото").click().run()
    assert app_test.sidebar.radio[0].value == "Аналіз фото"
    assert len(app_test.exception) == 0


def test_history_delete_requires_confirmation(app_test, repository, add_record, monkeypatch):
    analysis_id = add_record()
    monkeypatch.setattr("birdlab.config.DB_PATH", repository.db_path)
    monkeypatch.setattr("birdlab.config.UPLOAD_DIR", repository.upload_dir)
    app_test.run()
    app_test.sidebar.radio[0].set_value("Історія аналізів").run()
    assert app_test.button(key=f"delete_{analysis_id}").disabled
    app_test.checkbox(key=f"delete_confirm_{analysis_id}").check().run()
    app_test.button(key=f"delete_{analysis_id}").click().run()
    assert repository.get(analysis_id) is None and len(app_test.exception) == 0


def test_gallery_navigation_and_charts(app_test, repository, add_record, monkeypatch):
    analysis_id = add_record()
    monkeypatch.setattr("birdlab.config.DB_PATH", repository.db_path)
    monkeypatch.setattr("birdlab.config.UPLOAD_DIR", repository.upload_dir)
    app_test.run()
    app_test.sidebar.radio[0].set_value("Галерея птахів").run()
    app_test.button(key=f"gallery_detail_{analysis_id}").click().run()
    assert app_test.sidebar.radio[0].value == "Історія аналізів"
    assert len(app_test.exception) == 0
    app_test.sidebar.radio[0].set_value("Статистика").run()
    assert len(app_test.get("plotly_chart")) == 5 and len(app_test.exception) == 0
    assert not any("deprecated" in warning.value for warning in app_test.warning)


def test_delete_export_error_survives_rerun(app_test, repository, add_record, monkeypatch):
    from birdlab.errors import StorageError

    analysis_id = add_record()
    monkeypatch.setattr("birdlab.config.DB_PATH", repository.db_path)
    monkeypatch.setattr("birdlab.config.UPLOAD_DIR", repository.upload_dir)
    app_test.run()
    app_test.sidebar.radio[0].set_value("Історія аналізів").run()
    monkeypatch.setattr("birdlab.service.write_csv", Mock(side_effect=StorageError("Закрийте CSV в Excel")))
    app_test.checkbox(key=f"delete_confirm_{analysis_id}").check().run()
    app_test.button(key=f"delete_{analysis_id}").click().run()
    assert repository.get(analysis_id) is None
    assert any("Закрийте CSV" in warning.value for warning in app_test.warning)
