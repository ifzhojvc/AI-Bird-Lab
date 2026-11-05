import streamlit as st

from birdlab.errors import BirdLabError
from birdlab.files import load_audio, load_image, sha256
from birdlab.service import AnalysisService, sample_manifest
from birdlab.ui.common import history_button, predictions


def _show_saved(service: AnalysisService, kind: str, digest: str) -> None:
    saved = st.session_state.get(f"last_{kind}")
    if saved and saved["digest"] == digest:
        record = service.repository.get(saved["id"])
        if record:
            predictions(record)
            history_button(record["id"], f"history_{kind}_result")


def photo_page(service: AnalysisService) -> None:
    st.title("Аналіз фото")
    st.write("Завантажте фотографію та дослідіть три найближчі класи моделі ViT.")
    st.warning("Класифікатор обирає серед 200 класів CUB. Він не перевіряє наявність птиці й може призначити вид навіть предмету чи порожньому кадру.")
    single, batch = st.tabs(["Одне зображення", "Пакетний аналіз"])
    with single:
        uploaded = st.file_uploader("Фотографія JPG / JPEG / PNG", type=["jpg", "jpeg", "png"], key="photo_file", help="До 20 МБ та 25 мільйонів пікселів")
        if uploaded:
            data = uploaded.getvalue()
            try:
                image = load_image(data, uploaded.name)
            except BirdLabError as exc:
                st.error(str(exc))
            else:
                with st.container(border=True):
                    st.image(image, caption=uploaded.name, width="stretch")
                if st.button("Проаналізувати фото", type="primary", key="analyze_photo"):
                    try:
                        with st.spinner("Завантаження моделі та аналіз зображення…"):
                            analysis_id = service.analyze(data, uploaded.name, "image")
                        st.session_state.last_image = {"id": analysis_id, "digest": sha256(data)}
                        st.success(f"Аналіз №{analysis_id} збережено у SQLite.")
                        if service.last_warning:
                            st.warning(service.last_warning)
                    except BirdLabError as exc:
                        st.error(str(exc))
                _show_saved(service, "image", sha256(data))
        else:
            st.info("Додайте файл, щоб переглянути його та запустити аналіз.")
    with batch:
        rows = sample_manifest()
        st.subheader("Навчальний набір Wikimedia Commons")
        st.write(f"Доступно {len(rows)} фотографій із джерелами, ліцензіями та перевіреними мітками у sample_manifest.csv.")
        st.caption("Для еталонних фото перевіряється SHA-256. Оцінка якості стосується лише цього малого набору; його незалежність від навчальних даних не встановлено.")
        if st.button("Проаналізувати весь набір", type="primary", disabled=not rows, key="analyze_samples"):
            progress = st.progress(0.0, text="Підготовка набору…")
            with st.spinner("Пакетний аналіз…"):
                st.session_state.batch_results = service.batch_samples(lambda value, name: progress.progress(value, text=name))
        files = st.file_uploader("Або додайте власні фотографії", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="batch_files")
        if st.button("Проаналізувати вибрані файли", disabled=not files, key="analyze_custom_batch"):
            progress = st.progress(0.0, text="Підготовка файлів…")
            with st.spinner("Пакетний аналіз…"):
                st.session_state.batch_results = service.batch([(f.name, f.getvalue(), None) for f in files], lambda value, name: progress.progress(value, text=name))
        if "batch_results" in st.session_state:
            results = st.session_state.batch_results
            st.write(f"Збережено: {sum(r['id'] is not None for r in results)}; помилок: {sum(r['id'] is None for r in results)}.")
            st.dataframe([{"Файл": r["file"], "ID": r["id"], "Результат обробки": r["status"], "Примітка": r["warning"]} for r in results], hide_index=True, width="stretch")


def audio_page(service: AnalysisService) -> None:
    st.title("Аналіз аудіо")
    st.write("Розпізнавання пташиних звуків моделлю Wav2Vec2.")
    st.warning("Модель має 21 пташиний клас із локального набору Vedanthangal та клас фону. Сторонні звуки, інші види й низька якість можуть спричинити помилку.")
    st.caption("WAV, FLAC, MP3 · до 50 МБ · 0,25–60 с · mono / 16 000 Гц після перетворення. Довші записи обріжте. Аналіз сегментами по 5 с, зважене за тривалістю усереднення всіх класів.")
    with st.expander("Види та обмеження зіставлення"):
        from birdlab.config import ROOT
        import json

        path = ROOT / "verification" / "sources" / "audio_config.json"
        if path.exists():
            labels = json.loads(path.read_text(encoding="utf-8"))["id2label"]
            st.write(", ".join(labels.values()))
        st.info("White_Ibis та Golden_oriole не зіставляються з науковою назвою: метадані автора не знімають неоднозначність. background означає фон.")
    uploaded = st.file_uploader("Аудіозапис птахів", type=["wav", "flac", "mp3"], key="audio_file")
    if uploaded:
        data = uploaded.getvalue()
        try:
            audio = load_audio(data, uploaded.name)
        except BirdLabError as exc:
            st.error(str(exc))
            return
        st.audio(data)
        st.info(f"{audio.duration:.2f} с · початкова частота {audio.original_rate} Гц · каналів {audio.original_channels}")
        if st.button("Проаналізувати аудіо", type="primary", key="analyze_audio"):
            try:
                with st.spinner("Завантаження моделі та аналіз аудіозапису…"):
                    analysis_id = service.analyze(data, uploaded.name, "audio")
                st.session_state.last_audio = {"id": analysis_id, "digest": sha256(data)}
                st.success(f"Аналіз №{analysis_id} збережено у SQLite.")
                if service.last_warning:
                    st.warning(service.last_warning)
            except BirdLabError as exc:
                st.error(str(exc))
        _show_saved(service, "audio", sha256(data))
    else:
        st.info("Додайте запис пташиного співу. Початкове завантаження моделі може тривати кілька хвилин.")
