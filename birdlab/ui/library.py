import pandas as pd
import streamlit as st

from birdlab.config import UNKNOWN
from birdlab.errors import BirdLabError
from birdlab.export import csv_bytes
from birdlab.service import AnalysisService
from birdlab.statistics import filter_gallery
from birdlab.taxonomy import compare_taxa, load_catalog
from birdlab.ui.common import FIELDS, display_label, history_button, navigate, predictions, record_table


def show_media(record: dict, service: AnalysisService) -> None:
    path = service.repository.media_path(record)
    if not path.is_file():
        st.warning("Пов'язаний файл не знайдено. Збережені передбачення залишаються доступними.")
    elif record["analysis_type"] == "image":
        st.image(str(path), caption=record["original_name"], width="stretch")
    else:
        st.audio(path.read_bytes())


def history_page(service: AnalysisService) -> None:
    st.title("Історія аналізів")
    cols = st.columns([2, 1, 1])
    search = cols[0].text_input("Пошук за назвою птаха", key="history_search")
    kind_label = cols[1].selectbox("Тип аналізу", ["Усі", "Фото", "Аудіо"], key="history_kind")
    order = cols[2].selectbox("Сортування за датою", ["Спочатку нові", "Спочатку старі"], key="history_order")
    records = service.repository.all(search, {"Фото": "image", "Аудіо": "audio"}.get(kind_label), order == "Спочатку нові")
    st.download_button("Завантажити CSV поточної вибірки", csv_bytes(records), "bird_analysis.csv", "text/csv", key="download_history_csv")
    if not records:
        st.info("Історія порожня або жоден запис не відповідає фільтрам.")
    else:
        st.dataframe(record_table(records), hide_index=True, width="stretch")
        ids = [r["id"] for r in records]
        wanted = st.session_state.get("open_record")
        chosen = st.selectbox("Деталі запису", ids, index=ids.index(wanted) if wanted in ids else 0, format_func=lambda value: f"№{value} · {next(r['original_name'] for r in records if r['id'] == value)}", key=f"history_selected_{wanted}")
        record = service.repository.get(chosen)
        if record:
            with st.container(border=True):
                show_media(record, service)
                predictions(record)
                confirmed = st.checkbox("Підтверджую видалення цього запису та його файлу", key=f"delete_confirm_{chosen}")
                if st.button("Видалити запис", disabled=not confirmed, key=f"delete_{chosen}"):
                    service.repository.delete(chosen)
                    service.refresh_export()
                    if service.last_warning:
                        st.session_state.flash_warning = service.last_warning
                    st.session_state.pop("open_record", None)
                    st.rerun()
    with st.expander("Очищення всієї історії"):
        confirmed = st.checkbox("Підтверджую видалення всіх аналізів і збережених копій файлів", key="clear_confirm")
        st.caption("Оригінали у sample_images та їхній маніфест зберігаються.")
        if st.button("Очистити історію", disabled=not confirmed, key="clear_history"):
            service.repository.clear()
            service.refresh_export()
            if service.last_warning:
                st.session_state.flash_warning = service.last_warning
            st.session_state.pop("open_record", None)
            st.rerun()


def gallery_page(service: AnalysisService) -> None:
    st.title("Галерея птахів")
    records = service.repository.all(kind="image")
    if not records:
        st.info("Галерея з'явиться після першого фотоаналізу.")
        return
    filters = []
    for col, key, label in zip(st.columns(3), ("family", "habitat", "diet"), ("Родина", "Середовище існування", "Тип живлення")):
        values = sorted({r["bird"].get(key) or UNKNOWN for r in records})
        value = col.selectbox(label, ["Усі"] + values, key=f"gallery_{key}")
        filters.append("" if value == "Усі" else value)
    records = filter_gallery(records, *filters)
    st.caption(f"Знайдено фотографій: {len(records)}. Назви — передбачення моделі.")
    columns = st.columns(3)
    for index, record in enumerate(records):
        with columns[index % 3], st.container(border=True):
            path = service.repository.media_path(record)
            if path.is_file():
                st.image(str(path), width="stretch")
            else:
                st.info("Файл відсутній")
            st.markdown(f"**{display_label(record['predicted_species'], 'image')}**")
            st.write(f"Confidence: {record['confidence']:.2%}")
            st.caption(record["analysis_date"][:19].replace("T", " ") + " UTC")
            st.button("Переглянути деталі", key=f"gallery_detail_{record['id']}", on_click=navigate, args=("Історія аналізів", record["id"]))


def compare_page(service: AnalysisService) -> None:
    st.title("Порівняння видів")
    species_tab, modality_tab = st.tabs(["Довідкові характеристики", "Фото та аудіо"])
    records = service.repository.all()
    with species_tab:
        options = dict(load_catalog())
        for record in records:
            key = record["scientific_name"] or f"Невідомий таксон: {record['model_id']} / {record['predicted_species']}"
            options.setdefault(key, record["bird"] or {"english_name": record["predicted_species"]})
        keys = sorted(options)
        if len(keys) < 2:
            st.info("Для порівняння потрібні два види у довіднику або історії.")
        else:
            left, right = st.columns(2)
            label_for = lambda key: f"{options[key].get('ukrainian_name') or options[key].get('english_name') or UNKNOWN} · {key}"
            first = left.selectbox("Перший птах", keys, format_func=label_for, key="compare_first")
            second = right.selectbox("Другий птах", keys, index=1, format_func=label_for, key="compare_second")
            fields = dict(FIELDS, facts="Цікаві факти")
            frame = pd.DataFrame({"Характеристика": list(fields.values()), f"1 · {first}": [options[first].get(key) or UNKNOWN for key in fields], f"2 · {second}": [options[second].get(key) or UNKNOWN for key in fields]})
            st.dataframe(frame, hide_index=True, width="stretch", row_height=80)
            for key in dict.fromkeys([first, second]):
                with st.expander(f"Джерела: {key}"):
                    for url in options[key].get("sources", []):
                        st.markdown(f"[Відкрити джерело]({url})")
    with modality_tab:
        photos = [r for r in records if r["analysis_type"] == "image"]
        audio = [r for r in records if r["analysis_type"] == "audio"]
        st.warning("Збіг таксономічних назв не доводить, що фото й аудіо належать одній особині. Це зіставлення двох передбачень.")
        if not photos or not audio:
            st.info("Спочатку виконайте хоча б один фотоаналіз та один аудіоаналіз.")
        else:
            left, right = st.columns(2)
            describe = lambda r: f"№{r['id']} · {r['original_name']} · {r['predicted_species']}"
            first = left.selectbox("Результат фото", photos, format_func=describe, key="compare_photo")
            second = right.selectbox("Результат аудіо", audio, format_func=describe, key="compare_audio")
            st.info(compare_taxa(first["scientific_name"], second["scientific_name"]))
            st.write("Наукова назва (фото):", first["scientific_name"] or UNKNOWN)
            st.write("Наукова назва (аудіо):", second["scientific_name"] or UNKNOWN)
