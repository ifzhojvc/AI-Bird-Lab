import streamlit as st

from birdlab.config import AUDIO_MODEL, IMAGE_MODEL, ROOT
from birdlab.service import AnalysisService
from birdlab.statistics import build_charts, quality_metrics, summarize
from birdlab.ui.common import metrics, navigate


def home_page(service: AnalysisService) -> None:
    st.markdown('<div class="hero"><div class="eyebrow">ПРАКТИЧНА ЛАБОРАТОРІЯ · COMPUTER VISION + AUDIO</div><h1>AI Bird Lab</h1><p>Досліджуйте птахів за фотографіями та звуками. Порівнюйте модельні результати, перевіряйте джерела та зберігайте власну історію спостережень.</p></div>', unsafe_allow_html=True)
    metrics(service.repository.all())
    st.write("")
    for column, title, text, page, button in zip(st.columns(3), ("Зображення → вид", "Звук → клас", "Дані → висновки"), ("Vision Transformer порівнює фото з 200 класами птахів CUB і повертає TOP-3.", "Wav2Vec2 аналізує пташині голоси: 21 пташиний клас та фоновий звук.", "SQLite, ліцензовані зразки, CSV та інтерактивна статистика з окремою оцінкою якості."), ("Аналіз фото", "Аналіз аудіо", "Статистика"), ("Дослідити фото", "Дослідити аудіо", "Переглянути статистику")):
        with column, st.container(border=True):
            st.subheader(title)
            st.write(text)
            st.button(button, key=f"home_{page}", on_click=navigate, args=(page,))
    st.info("Моделі запускаються локально. Початкові ваги завантажуються з Hugging Face при першому аналізі; після цього доступний офлайн-режим.")
    st.caption("Результат класифікатора — гіпотеза. Confidence не є виміряною точністю, а кількість розпізнаних класів не підтверджує біорізноманіття місцевості.")


def statistics_page(service: AnalysisService) -> None:
    st.title("Статистика")
    records = service.repository.all()
    st.caption("Статистика модельних передбачень. Фоновий клас не входить у кількість видів; непідтверджені таксони враховуються як окремі модельні класи.")
    metrics(records)
    if not records:
        st.info("Даних ще немає. Виконайте аналіз, щоб побачити графіки.")
        return
    summary = summarize(records)
    cols = st.columns(3)
    cols[0].metric("Середній confidence", f"{summary['average_confidence']:.2%}")
    cols[1].metric("Найвищий confidence", f"{summary['max_record']['confidence']:.2%}", help=summary["max_record"]["predicted_species"])
    cols[2].metric("Найнижчий confidence", f"{summary['min_record']['confidence']:.2%}", help=summary["min_record"]["predicted_species"])
    st.write("Найчастіші результати:", ", ".join(f"{label} ({count})" for label, count in sorted(summary["species_counts"].items(), key=lambda item: item[1], reverse=True)[:3]))
    charts = build_charts(records)
    columns = st.columns(2)
    for index, (title, chart) in enumerate(charts.items()):
        with columns[index % 2], st.container(border=True):
            st.subheader(title)
            st.plotly_chart(chart, use_container_width=True, config={"displayModeBar": False, "responsive": True}, key=f"chart_{index}")
    st.subheader("Якість на розмічених фотографіях")
    quality = quality_metrics(service.repository.evaluations())
    if not quality:
        st.info("Немає перевірених еталонних міток. Accuracy не обчислюється.")
    for group in quality:
        with st.container(border=True):
            st.write(group["model_id"], "·", group["experiment"])
            cols = st.columns(3)
            cols[0].metric("Top-1 accuracy", f"{group['top1_accuracy']:.2%}")
            cols[1].metric("Top-3 accuracy", f"{group['top3_accuracy']:.2%}")
            cols[2].metric("Розмічених прикладів", group["count"])
            st.write(f"Правильних Top-1: {group['correct']}; неправильних: {group['incorrect']}.")
    st.warning("Малий набір Wikimedia має мітки зі сторінок видів. Це навчальна оцінка на конкретних прикладах, без гарантії незалежності від тренувального набору. Вона не оцінює всі 200 класів і не вимірює якість аудіомоделі.")


def about_page(service: AnalysisService) -> None:
    st.title("Про проєкт")
    st.write("AI Bird Lab — практична робота з локальної класифікації фото та звуків птахів.")
    st.write("Виконав: Бахін Микита Максимович · Група: ЕЗ-25-1")
    st.subheader("Моделі")
    st.markdown(f"[ViT CUB-200 · {IMAGE_MODEL}](https://huggingface.co/{IMAGE_MODEL})")
    st.write("Vision Transformer, 200 іменованих класів, RGB-зображення. Автоматичне використання CUDA, якщо доступна; інакше CPU.")
    st.markdown(f"[Wav2Vec2 · {AUDIO_MODEL}](https://huggingface.co/{AUDIO_MODEL})")
    st.write("Wav2Vec2ForSequenceClassification, mono-аудіо 16 кГц, 22 виходи: 21 пташиний клас і фон. Два неоднозначні класи не зіставляються з таксономією.")
    st.warning("Початково в завданні було вказано HaotianZG/vit-cub-200-2011-bird. Перевірка config.json та вихідного шару її ваг показала 1000 класів ImageNet. За погодженням із замовником використано перевірену 200-класову заміну; докази збережено у verification/sources.")
    st.subheader("Джерела й обмеження")
    st.write("Довідник перевіряє наукові назви через Wikidata P225 та точні збіги GBIF. Відсутні дані позначаються «Немає даних». Модельні мітки зіставляються лише явним переліком відповідностей, без нечіткого пошуку.")
    st.write("Оригінали залишаються локально у sample_images, робочі копії — у uploads. Класифікація не передає завантажені медіафайли зовнішньому сервісу. Оновлення довідки надсилає GBIF лише перевірену наукову назву.")
    st.markdown("[Wikimedia Commons: повторне використання](https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia)")
    for name, label in (("README.md", "Інструкція користувача"), ("report.md", "Звіт для викладача"), ("sample_manifest.csv", "Джерела та ліцензії фотографій")):
        path = ROOT / name
        if path.exists():
            st.download_button(label, path.read_bytes(), name, key=f"about_{name}")
