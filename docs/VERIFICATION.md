# Протокол перевірки AI Bird Lab 2.0

Дата: 28.10.2026. Перевірка виконана на Windows у наявному проєкті з локальним SQL Express та кешованими моделями. Фізичний iPhone не підключався.

## Результати

| Перевірка | Фактично отримано | Доказ |
| --- | --- | --- |
| Python, повний набір | **115 passed**, 1 deprecation warning anyio/Starlette; включно з 3 реальними integration-тестами | `verification/python-complete.xml` |
| ASP.NET/EF/сервіси/CSV/AI-контракт | **20 passed**, 0 skipped | `verification/central-server-tests.trx` |
| React TypeScript | успішно | `npm run typecheck` |
| HTTP-клієнт вебу / спільний контракт | **5 passed** | `web-app/src/api.test.ts`, vitest |
| React/Vite production build | успішно; main JS ~330 КБ, lazy statistics ~369 КБ | `npm run build` |
| Mobile TypeScript | успішно | `npm run typecheck` |
| Expo dependency matrix | сумісні версії SDK 57 / RN 0.86.3 | `expo install --check`, lock-файл |
| expo-doctor | **21/21 passed** | фактичний CLI-запуск після вирівнювання peer dependencies |
| iOS JS bundle | успішний export **966 modules**, `--no-bytecode` на Windows | `mobile-app/.test-artifacts/ios-export` — відновлюваний build, не включається до здачі |
| Metro manifest iOS | HTTP manifest із launchAsset отримано | `verification/mobile-protocol.json` |
| M4A/AAC | реальний M4A → FastAPI FFmpeg → Wav2Vec2 → SQL, ID 36 | `verification/mobile-protocol.json` |
| LAN API | `/api/health` доступний за фактичною LAN-адресою ПК | `verification/mobile-protocol.json` |
| Початковий імпорт | 16 аналізів / 48 TOP-передбачень / 15 оцінок | `verification/migration-first.json` |
| Повторний імпорт | 0 нових, 16 пропущено, кількості перевірені | `verification/migration-repeat.json` |
| Реальна повна HTTP-інтеграція | **12 сценаріїв**, `mock_used: false` | `verification/client-server-real.json` |
| Реальний збій AI | health 503, prediction 502, SQL-історія й файлове сховище не змінились | `verification/ai-outage.json` |
| Завершальна збірка/API | Swagger із полями статистики, реальний save/read/delete, узгоджена статистика | `verification/final-api-check.json` |
| Захист початкових даних | **37 файлів** з незмінними SHA-256 | `verification/delivery-check.json` |
| Компактний комплект | папка submission до 25 МБ; 16 uploads відновлено в ізольованій копії, всі файли SQLite звірено за hash, повторне відновлення створило 0 копій | `verification/submission-roundtrip.json` |
| Коментарі у вихідному коді | не виявлено у перевірених Python/C#/TS/TSX/JS/PS1 джерелах | `verification/delivery-check.json` |
| Docker Compose | синтаксис і підстановки перевірені `docker compose config --quiet` із тимчасовими випадковими значеннями | контейнери не запускалися |

115 Python-тестів: 99 початкових unit/UI-тестів, 10 FastAPI unit-тестів, 3 тести точного відновлення uploads, 2 початкових реальних integration-тести та 1 реальний HTTP TestClient-тест фото+аудіо. Unit-підміни чітко відокремлені від справжньої моделі. 20 тестів .NET включають FileStore, path traversal, очищення невдалої загрузки, CSV, відповідність EF snapshot, збереження/пошук/видалення у тестовому EF InMemory, відмови HTTP, mock/rank/metadata-валідацію. InMemory-тести не видаються за SQL integration: SQL підтверджено окремим реальним HTTP-протоколом.

## Справжня інтеграція

Використано дві незалежні `requests.Session`, що моделюють HTTP-поведінку вебу та телефона. Це протокол клієнтів, а не твердження про запуск React Native на пристрої.

Перевірено: створення фото через одну сесію та читання іншою; зворотний напрямок; аудіомодель; SHA-256 завантаженого медіа; Range 206; відхилення пошкодженого зображення без збереження; параметри історії; довідник і порівняння; **всі 15 оригінальних фото через `/analysis/batch`**; BOM і кількість рядків CSV; видалення власного тестового запису та його медіа; узгодженість статистики; незмінність вихідних файлів.

Початкова SQL-історія мала 16 записів; протокол залишив 17 власних нових записів після видалення одного тестового. Подальші окремі браузерні фото/аудіо та M4A-перевірка додали ще результати. Актуальна кількість під час завершальної перевірки фіксується в `final-api-check.json`. Оригінальна SQLite залишається з 16 записами.

## Справжній браузер

Через React виконані фотоаналіз №35 та аудіоаналіз №37, відображені TOP-3 та довідкові картки. Перевірені пошук `Cardinalis` в історії, статистика, вибір двох видів і двох моделей. На головній видно серверні показники та реальне зображення з API.

Знімки:

- [Настільна головна](../verification/screenshots/web-client-desktop.png).
- [Веб на ширині 390×844](../verification/screenshots/web-client-phone.png).
- [Справжній фотоаналіз](../verification/screenshots/web-client-real-photo.png).
- [Справжній аудіоаналіз](../verification/screenshots/web-client-real-audio.png).
- [Порівняння видів і моделей](../verification/screenshots/web-client-compare.png).

При 390×844: `document.documentElement.scrollWidth = 375`, `window.innerWidth = 390` (враховано смугу прокручування), broken images = 0. Це перевірка мобільного браузерного layout, а не iPhone Expo Go. Після цих перевірок вбудований браузер повідомив `ERR_NETWORK_IO_SUSPENDED`; подальша браузерна перевірка стану AI-error не була зарахована. Сам реальний відказ AI перевірений HTTP-скриптом.

## Межі та відомі обмеження

- Камера, мікрофон, Expo Go QR, iOS Local Network, Safari доступ із самого iPhone та системний CSV Share потребують ручного тесту на фізичному пристрої. Є [покроковий протокол](IPHONE.md).
- iOS bundle підтверджує розв’язання модулів і можливість JS-збірки; він не є нативним build і не доводить пристрійний runtime.
- Compose не розгортався, оскільки Docker daemon не працював. Локальна Windows-архітектура перевірена незалежно від Docker.
- API спільної навчальної історії працює без акаунтів. Контроль доступу для публічного production-розгортання не реалізувався як частина цього завдання.
- Порівняння двох модельних передбачень не підтверджує тотожність особини. Аудіозразок robin не входить до класів моделі; збережено буквальний результат `Rosy_starling`, а не вигадане розпізнавання вільшанки.
- У першому sandbox-запуску 99 початкових тестів пройшли, але cleanup системної TEMP-папки отримав WinError 5. У фінальному запуску TEMP перенаправлено до `.test-artifacts` і виконано весь набір без цієї помилки.
- Sandbox також заборонив локальні сокети WinError 10013 / testhost handshake. Дозволені повторні перевірки поза sandbox успішно встановили HTTP та SQL-з’єднання. Початкові невдалі запуски не вважаються інтеграційними успіхами.

## Відтворення

Команди основного README відтворюють unit, build та real HTTP перевірки. `verify_mobile_protocol.py` додатково потребує запущеного Metro та налаштованого `mobile-app/.env`. Для `verify_ai_outage.py` зупиніть тільки власний FastAPI, залишивши SQL та ASP.NET, а після перевірки відновіть AI. `verify_final.py` перевіряє успішний цикл уже після відновлення. Ці скрипти не звертаються до платних AI API.
