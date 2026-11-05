import logging

import streamlit as st

from birdlab.config import CSV_PATH, DB_PATH, UPLOAD_DIR
from birdlab.errors import BirdLabError
from birdlab.repository import Repository
from birdlab.service import AnalysisService
from birdlab.ui.analysis import audio_page, photo_page
from birdlab.ui.common import PAGES, style
from birdlab.ui.library import compare_page, gallery_page, history_page
from birdlab.ui.overview import about_page, home_page, statistics_page


def main() -> None:
    st.set_page_config(page_title="AI Bird Lab · Лабораторія птахів", page_icon="🪶", layout="wide")
    style()
    with st.sidebar:
        st.markdown('<div class="brand">🪶 AI Bird Lab</div>', unsafe_allow_html=True)
        st.caption("Птахи. Моделі. Спостереження.")
        st.radio("Навігація", PAGES, key="page", label_visibility="collapsed")
        st.divider()
        offline = st.toggle("Офлайн-режим", value=False, key="offline")
        online_reference = st.toggle("Оновлювати таксономію через GBIF", value=False, disabled=offline, key="online_reference")
        st.caption("Моделі завантажуються лише під час аналізу. Довідкові дані кешуються на 24 години.")
    try:
        repository = Repository(DB_PATH, UPLOAD_DIR)
        service = AnalysisService(repository, offline, online_reference, CSV_PATH)
        if warning := st.session_state.pop("flash_warning", None):
            st.warning(warning)
        if not CSV_PATH.exists():
            service.refresh_export()
            if service.last_warning:
                st.warning(service.last_warning)
        pages = dict(zip(PAGES, (home_page, photo_page, audio_page, history_page, gallery_page, compare_page, statistics_page, about_page)))
        pages[st.session_state.page](service)
    except BirdLabError as exc:
        st.error(str(exc))
    except (OSError, ValueError) as exc:
        logging.exception("Помилка обробки локальних даних")
        st.error(f"Не вдалося обробити локальні дані. Перевірте файли та права доступу. Тип помилки: {type(exc).__name__}.")


if __name__ == "__main__":
    main()
