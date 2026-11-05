import html

import pandas as pd
import streamlit as st

from birdlab.config import UNKNOWN
from birdlab.taxonomy import resolve_label


PAGES = ["Головна", "Аналіз фото", "Аналіз аудіо", "Історія аналізів", "Галерея птахів", "Порівняння видів", "Статистика", "Про проєкт"]
FIELDS = {"ukrainian_name": "Українська назва", "english_name": "Англійська назва", "scientific_name": "Наукова назва", "family": "Родина", "habitat": "Середовище існування", "range": "Географічне поширення", "diet": "Живлення", "size": "Розміри", "conservation_status": "Природоохоронний статус"}


def navigate(page: str, analysis_id: int | None = None) -> None:
    st.session_state.page = page
    if analysis_id is not None:
        st.session_state.open_record = analysis_id


def display_label(label: str, kind: str) -> str:
    if label == "background":
        return "Фоновий звук"
    bird = resolve_label(label, kind)
    return (bird.get("ukrainian_name") or bird.get("english_name") or label) if bird else label


def style() -> None:
    st.markdown("""<style>
    .block-container{max-width:1240px;padding-top:2.5rem;padding-bottom:3rem}
    [data-testid="stSidebar"]{border-right:1px solid #29383A}
    [data-testid="stMetric"]{background:#172225;border:1px solid #2A3A3A;border-radius:16px;padding:18px}
    [data-testid="stMetricLabel"]{color:#ACBEB5}
    [data-testid="stMetricValue"]{font-size:2rem;color:#A1E8BC}
    [data-testid="stVerticalBlockBorderWrapper"]>div{border-radius:16px}
    h1,h2,h3{letter-spacing:-.025em}
    .hero{padding:32px;border:1px solid #30483D;border-radius:24px;background:linear-gradient(120deg,#1A3428,#172225);margin-bottom:24px}
    .eyebrow{font-size:12px;letter-spacing:.18em;color:#9CE8B8;font-weight:700}
    .hero h1{font-size:clamp(2rem,4vw,3.4rem);line-height:1.1;margin:12px 0}
    .hero p{color:#C1D4C8;max-width:690px;font-size:1.05rem;margin:0}
    .brand{font-size:1.5rem;font-weight:750;letter-spacing:-.04em;color:#A1E8BC}
    .stButton>button{border-radius:10px}
    [data-testid="stFileUploader"]{border-radius:16px}
    [data-testid="stAppDeployButton"],[data-testid="stMainMenu"]{display:none}
    [data-testid="stFileUploaderDropzoneInstructions"]>div>span:first-child{font-size:0}
    [data-testid="stFileUploaderDropzoneInstructions"]>div>span:first-child::after{content:'Перетягніть файл сюди';font-size:14px}
    [data-testid="stFileUploaderDropzoneInstructions"]>div>span:nth-child(2){display:none}
    [data-testid="stFileUploaderDropzone"] button{font-size:0}
    [data-testid="stFileUploaderDropzone"] button::after{content:'Обрати файл';font-size:14px}
    @media(max-width:700px){.block-container{padding:4.75rem 1rem 1.5rem}.hero{padding:22px}.hero h1{font-size:2.2rem}}
    </style>""", unsafe_allow_html=True)


def metrics(records: list[dict]) -> None:
    from birdlab.statistics import summarize

    summary = summarize(records)
    for column, label, value in zip(st.columns(3), ("Проаналізовано фото", "Проаналізовано аудіо", "Унікальні види / класи"), (summary["images"], summary["audio"], summary["unique_species"])):
        column.metric(label, value)


def bird_card(bird: dict) -> None:
    with st.container(border=True):
        st.subheader("Довідка про птаха")
        st.caption(bird.get("reference_status", "Дані зі збереженого довідника"))
        left, right = st.columns(2)
        for index, (key, label) in enumerate(FIELDS.items()):
            with (left if index % 2 == 0 else right):
                st.markdown(f"**{label}**")
                st.write(bird.get(key) or UNKNOWN)
        st.markdown("**Цікаві факти**")
        st.write(bird.get("facts") or UNKNOWN)
        st.markdown("**Джерела інформації**")
        if bird.get("sources"):
            for url in bird["sources"]:
                st.markdown(f"[Відкрити джерело]({url})")
            st.caption("Довідкові описи Вікіпедії: CC BY-SA; посилання ведуть до авторства й історії змін. Дані можуть оновлюватися.")
        else:
            st.write(UNKNOWN)


def predictions(record: dict) -> None:
    st.subheader(display_label(record["predicted_species"], record["analysis_type"]))
    st.caption(f"Мітка моделі: {record['predicted_species']} · ID запису: {record['id']}")
    col1, col2 = st.columns(2)
    col1.metric("Confidence найвищого результату", f"{record['confidence']:.2%}")
    col2.metric("Час виконання моделі", f"{record['elapsed_seconds']:.2f} с")
    st.caption("Confidence — оцінка моделі серед її класів, а не гарантована ймовірність правильного визначення.")
    st.markdown("**TOP-3 модельних результатів**")
    for item in record["predictions"]:
        label = display_label(item["label"], record["analysis_type"])
        st.progress(float(item["score"]), text=f"{item['rank']}. {label} — {item['score']:.2%}")
        if label != item["label"]:
            st.caption(item["label"])
    if record["predicted_species"] == "background":
        st.warning("Найвищий результат — фоновий звук. Пташиний вид не визначено.")
    else:
        bird_card(record["bird"])
    with st.expander("Параметри аналізу та відтворюваність"):
        st.write("Модель:", record["model_id"])
        st.write("Ревізія:", record["model_revision"])
        st.write("Дата UTC:", record["analysis_date"])
        st.write("SHA-256:", record["file_hash"])
        st.json(record["metadata"])
    if record.get("evaluation"):
        evaluation = record["evaluation"]
        st.info(f"Еталон: {evaluation['expected_label']}. Top-1: {'збіг' if evaluation['top1_correct'] else 'розбіжність'}. Top-3: {'збіг' if evaluation['top3_correct'] else 'розбіжність'}.")


def history_button(analysis_id: int, key: str) -> None:
    st.button("Відкрити запис в історії", key=key, on_click=navigate, args=("Історія аналізів", analysis_id))


def record_table(records: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([{"ID": r["id"], "Тип": "Фото" if r["analysis_type"] == "image" else "Аудіо", "Файл": r["original_name"], "Вид / клас": display_label(r["predicted_species"], r["analysis_type"]), "Confidence, %": round(r["confidence"] * 100, 2), "Дата UTC": r["analysis_date"]} for r in records])
