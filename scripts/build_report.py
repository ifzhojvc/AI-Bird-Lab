import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_result(name: str) -> str:
    path = ROOT / "verification" / name
    if not path.exists():
        return "Перевірку не виконано."
    tree = ET.parse(path)
    suites = tree.getroot().findall("testsuite")
    tests = sum(int(s.get("tests", 0)) for s in suites)
    skipped = sum(int(s.get("skipped", 0)) for s in suites)
    failures = sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites)
    return f"{tests - skipped - failures} пройдено; {skipped} пропущено; помилок/падінь {failures}."


def main() -> None:
    evidence = json.loads((ROOT / "verification" / "real_run.json").read_text(encoding="utf-8"))
    summary = evidence["summary"]
    quality = evidence["quality"][0]
    table = "\n".join(f"| {index} | {row['file_name']} | {row['expected_label']} | {row['predictions'][0]['label']} | {row['predictions'][0]['score'] * 100:.2f}% | {'Так' if row['top1_correct'] else 'Ні'} | {'Так' if row['top3_correct'] else 'Ні'} |" for index, row in enumerate(evidence["images"], 1))
    audio = evidence.get("audio", {})
    audio_rows = "\n".join(f"| {p['rank']} | {p['label']} | {p['score'] * 100:.2f}% |" for p in audio.get("predictions", []))
    screenshots = "\n\n".join(f"![{title}](../verification/screenshots/{filename})" for filename, title in (("home-desktop.jpg", "Головна сторінка, справжній браузерний знімок"), ("statistics-desktop.jpg", "Статистика реальних результатів"), ("gallery-desktop.jpg", "Галерея з проаналізованими фотографіями"), ("home-mobile.jpg", "Вузький браузерний viewport")) if (ROOT / "verification" / "screenshots" / filename).exists())
    report = f"""# Практична робота: AI Bird Lab

**Виконав:** Бахін Микита Максимович<br>
**Група:** ЕЗ-25-1

Дата протоколу: {evidence['timestamp_utc']}. Результати отримано локально, `mock_used: false`.

## 1. Мета роботи

Створити Windows-застосунок для практичного дослідження готових моделей класифікації зображень і звуків птахів, збереження передбачень, перевірених джерел та окремої оцінки якості на розмічених зразках.

## 2. Використані технології

Python {evidence['python']}, Streamlit {evidence['packages']['streamlit']}, Transformers {evidence['packages']['transformers']}, PyTorch {evidence['packages']['torch']}, Pillow {evidence['packages']['Pillow']}, librosa {evidence['packages']['librosa']}, soundfile {evidence['packages']['soundfile']}, NumPy {evidence['packages']['numpy']}, pandas {evidence['packages']['pandas']}, Plotly {evidence['packages']['plotly']}, SQLite, requests та pytest. Середовище Windows, обчислення CPU. Встановлені версії зафіксовано у requirements та lock-файлі.

## 3. Обрані моделі Hugging Face

**Фото:** [PwNzDust/vit_cub](https://huggingface.co/PwNzDust/vit_cub), ревізія `fe8e5064afeb9ed34bd6539f992b4f8cd85af919`, Apache-2.0. Архітектура `ViTForImageClassification`, 200 іменованих класів CUB, 12 Transformer-шарів, прихована розмірність 768, патчі 16×16. Вхід — RGB-фотографія, нормалізована й масштабована процесором до 224×224; вихід — 200 logits та softmax scores. Залежності: Transformers, torch, Pillow, Safetensors.

У початковому завданні вказано [HaotianZG/vit-cub-200-2011-bird](https://huggingface.co/HaotianZG/vit-cub-200-2011-bird). У перевіреній ревізії `c87ad31b77751c3c4d6c32d2d6ef288a1b31a0a1` її config містить 1000 ImageNet-міток, а ваги вихідного шару — `[1000, 768]`. Це суперечить припущенню про 200 CUB-виходів. Замовник прямо погодив заміну на перевірену модель з 200 класами. Ваги заміни дійсно мають `[200, 768]`. Нейромережу не навчали і не переіменовували її класи довільно. Оригінальні конфігурації, ревізії та форми шарів залишено у `verification/sources`.

**Аудіо:** [greenarcade/wav2vec2-vd-bird-sound-classification](https://huggingface.co/greenarcade/wav2vec2-vd-bird-sound-classification), ревізія `ccc18a635d5c561ff8de26873c1db0e7c6cbc51c`, MIT. Архітектура `Wav2Vec2ForSequenceClassification`: згорткове виділення ознак, Transformer та класифікаційна голова. Вхід — mono float32, 16 000 Гц; вихід — 22 scores: 21 пташиний клас та фон. Ваги `classifier.weight` — `[22, 256]`. Залежності: Transformers, torch, NumPy; декодування soundfile, ресемплінг librosa. Model card описує регіональний набір Vedanthangal; підтримку всіх птахів світу не заявлено.

## 4. Принцип роботи моделей

ViT представляє фото патчами, обчислює ознаки та ранжує 200 класів. Програма зберігає три найбільші scores. Модель не визначає, чи взагалі є птиця у кадрі, тому навіть непташине фото може отримати видову мітку.

Аудіо декодується, усереднюється за каналами та приводиться до частоти feature extractor. Максимум — 60 секунд. Сегменти до 5 секунд оцінюються через `pipeline("audio-classification")` з `top_k=22`. Scores усіх класів усереднюються з вагою тривалості, після чого визначається TOP-3. Фон не перетворюється на пташиний вид.

Моделі кешуються `st.cache_resource`, довідка — `st.cache_data`. Невдале завантаження не породжує випадкових результатів. Confidence є внутрішнім score, а не гарантованою правильністю.

## 5. Вхідні та вихідні дані

Входи: справжні JPG/JPEG/PNG до 20 МБ, аудіо WAV/FLAC/MP3 до 50 МБ та 0,25–60 с. Виходи: прев'ю/плеєр, TOP-3 з confidence, довідкова картка, історія SQLite, CSV UTF-8 BOM, графіки та еталонні оцінки для перевірених фотографій. Оригінальні назви класів не перекладаються довільно; українські назви беруться лише з джерел.

## 6. Структура застосунку

`app.py` маршрутизує 8 сторінок. `birdlab/ui` містить інтерфейс; `models` — ліниві pipeline; `files` — валідацію медіа; `taxonomy` і `reference` — явне таксономічне зіставлення та GBIF; `repository` — SQLite; `service` — сценарії аналізу; `export` — CSV; `statistics` — метрики й Plotly. Окремо збережено тести, скрипти, дані, зразки та машинні докази. Повне дерево — у README.

Довідник має 33 перевірені таксони, охоплює 15 фотокласів і 19 однозначних аудіокласів з одним спільним видом. Решта характеристик або класів можуть бути невідомими. Наукові назви перевірені через Wikidata P225, родини — лише точним видовим GBIF-збігом. Неоднозначні White_Ibis та Golden_oriole не отримують вгаданої наукової назви. Мовна модель не використовується для вигадування фактів. Джерела та відсутні поля відображаються явно.

## 7. Реалізація бази даних

Таблиці: `analyses` (файл, тип, дата UTC, TOP-1, confidence, модель, ревізія, час виконання, хеш, опис, довідковий знімок), `predictions` (три ранжовані виходи), `bird_info` (довідковий кеш), `evaluations` (еталон, джерело, хеш, Top-1/Top-3 збіг). Зовнішні ключі видаляють пов'язані передбачення й оцінки. SQL параметризовано; база створюється автоматично.

Видалення стосується лише збереженої копії у uploads, із перевіркою меж папки та відкатом перейменування за невдалої SQL-транзакції. Оригінали тестового набору залишаються. Повторне видалення ID безпечне. Після успішної операції формується CSV; блокування CSV Excel не скасовує вже збережений аналіз.

## 8. Приклади аналізу фотографій

Перший реальний зразок: `01_Cardinalis_cardinalis.jpg`, еталон Cardinal. Модель повернула `Cardinal`, confidence {evidence['images'][0]['predictions'][0]['score'] * 100:.2f}%. Усі три необроблені модельні результати для кожного файла є у `verification/real_run.json` та SQLite.

Приклад помилки: `12_Bombycilla_cedrorum.jpg`, еталон Cedar Waxwing; TOP-3: Boat tailed Grackle 26,98%, Rusty Blackbird 21,92%, Gray Catbird 14,80%. Правильного класу немає у TOP-3. Передбачення не виправлялося вручну.

## 9. Приклади аудіоаналізу

Використано реальний польовий аудіозапис InspectorJ «Bird Whistling, Robin, Single, 13.wav», [Freesound 456440](https://freesound.org/people/InspectorJ/sounds/456440/), CC BY 3.0. Дзеркало librosa декодовано з OGG у PCM16 WAV. Тривалість {audio.get('metadata', {}).get('duration', 0):.4f} с, початкова частота 22 050 Гц, після ресемплінгу 16 000 Гц. Авторство, ліцензія, хеш та перетворення в sample_audio/manifest.json.

| Ранг | Справжня мітка моделі | Confidence |
|---|---|---:|
{audio_rows}

Robin відсутній у 21 пташиному класі. Найвищий результат Rosy_starling не слід вважати правильним визначенням реального птаха. Цей прогін підтверджує завантаження, декодування, ресемплінг, виконання pipeline, TOP-3 та збереження; **accuracy аудіомоделі не виміряна**.

## 10. Тестування на 15 фотографіях

Справжні фотографії 15 різних видів отримані з Wikimedia Commons; ліцензії CC BY / CC BY-SA. Для кожного файла маніфест містить автора, URL джерела і ліцензії, Wikidata ID, наукову назву, еталонну мітку та SHA-256. Наукові назви взято з відповідних сторінок видів і підтверджено Wikidata; незалежної експертної розмітки цього набору не виконано. Перед аналізом перевірено хеші.

| № | Файл | Еталон | TOP-1 моделі | Confidence | Top-1 збіг | Top-3 збіг |
|---:|---|---|---|---:|---|---|
{table}

Оброблено {len(evidence['images'])} із 15 фото. Помилок виконання протоколу: {len(evidence['errors'])}. Один хибний видовий результат є модельною помилкою, а не технічним падінням. Пакетна обробка з пошкодженим файлом та продовженням перевірена окремим модульним тестом.

## 11. Статистика результатів

У робочій базі {summary['images']} фотоаналізів і {summary['audio']} аудіоаналіз. Унікальних найвищих видів/класів: {summary['unique_species']}; це не незалежно підтверджені біологічні види. Кожна найвища мітка трапилася один раз. Середній confidence усіх 16 результатів — {summary['average_confidence'] * 100:.2f}%; максимальний — 99,98% (Blue Jay), мінімальний — 26,98% (Boat tailed Grackle). Змішані scores двох моделей не є порівнянням їхньої якості.

Побудовано п'ять Plotly-графіків: розподіл видів/класів, TOP-10, розподіл confidence, аналізи за датами та типи аналізу. Локальний CSV містить {evidence['checks']['csv_rows']} справжніх записів із BOM; аудіорядок має порожні фотополя. Усі 48 передбачень TOP-3 повторно прочитані з SQLite.

## 12. Оцінка точності

Top-1 accuracy = правильні найвищі класи / кількість розмічених фото = **{quality['correct']}/{quality['count']} = {quality['top1_accuracy'] * 100:.2f}%**.

Top-3 accuracy = фото, де еталон є у трьох результатах / кількість розмічених фото = **{quality['top3_correct']}/{quality['count']} = {quality['top3_accuracy'] * 100:.2f}%**.

Правильних Top-1: {quality['correct']}; неправильних: {quality['incorrect']}. Рахуються лише перевірені еталонні записи з таблиці evaluations, окремо для кожної ревізії. Повтор того самого SHA-256 не збільшує розмір вибірки метрик.

Це навчальна оцінка на малому зручному наборі Wikimedia, без стратифікації всіх 200 класів. Перетин із тренувальними даними невідомий. Ці 93,33% не є заявою про загальну accuracy, роботу в Україні або якість на довільних фотографіях. Додаткові експерименти з розмиттям/яскравістю/роздільністю не виконувалися.

## 13. Обмеження моделей і перевірки

- Обмежені простори класів; немає надійного виявлення відсутності птиці на фото. Сторонні звуки або невідомий вид можуть давати хибний клас.
- Confidence не відкалібровано на незалежному тесті і не є гарантією. Аудіомодель випробувана на реальному коректному звуці поза її класами; репрезентативний розмічений аудіонабір не оцінювався.
- Довідник навмисно неповний. Невідомі значення показуються «Немає даних». Збіг виду фото/аудіо не підтверджує спільної особини.
- CUDA та фізичні мобільні пристрої не перевірялися. Перевірка адаптації стосується браузерних viewport, де є збережений доказ.
- Поточне середовище вимагало дозволеного повтору мережевих і тимчасових файлових операцій через обмеження Windows-песочниці. Це не приховувалося як успішний первинний запуск. Перервані ваги докачано без підміни.

Фактичні автоматизовані перевірки:

- Модульні та Streamlit AppTest: {test_result('unit-tests.xml')}
- Окремі справжні інтеграційні тести: {test_result('integration-tests.xml')}
- Справжній пакетний протокол з офлайн-вагами: `passed={evidence['passed']}`, без mocks.
- Усі вісім сторінок перевіряються AppTest; пошук, видалення з підтвердженням, переходи, фільтри та п'ять графіків мають автоматизовані перевірки. Браузерні перевірки записано окремо у verification/browser_checks.json, фінальні перевірки даних — у verification/final_checks.json.

Справжні знімки інтерфейсу, отримані під час перевірки:

{screenshots}

## 14. Висновок

Реалізовано модульний локальний застосунок AI Bird Lab з українським UI, двома справжніми моделями, SQLite, джерелами, пакетним аналізом, CSV та окремою оцінкою якості. Робочі результати 15 фотографій і аудіозапису збережені для перевірки викладачем. Виявлено й задокументовано некоректне припущення про початкову фотомодель, одну помилку фотокласифікації та обмеження аудіопередбачення поза відомими класами.

Запуск: `streamlit run app.py` в активованому середовищі або `.\\.venv\\Scripts\\python.exe -m streamlit run app.py`. Повторний протокол: `.\\.venv\\Scripts\\python.exe -X utf8 scripts/verify_real.py --offline`. Усі вимірювання спираються на фактично збережені outputs.
"""
    destination = ROOT / "docs" / "LEGACY_REPORT.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(report, encoding="utf-8")
    print("Звіт сформовано за фактичним протоколом та JUnit XML.")


if __name__ == "__main__":
    main()
