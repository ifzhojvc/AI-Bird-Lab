> Оновлення 03.11.2026: користувацькі маршрути тепер потребують сесії Identity. Історія та медіа приватні, batch/compare/statistics/gallery перевіряють тариф. Повні auth/subscription/wallet endpoints і політики: [SUBSCRIPTIONS.md](SUBSCRIPTIONS.md).

# HTTP API

Центральний origin за замовчуванням: `http://localhost:5100`. Swagger UI: `/swagger`, OpenAPI JSON: `/swagger/v1/swagger.json`. Усі клієнтські маршрути починаються з `/api`. ID історії залишаються додатними цілими числами; UUID analysisId ідентифікує асинхронне завдання. Контракти RabbitMQ описані в [RABBITMQ.md](RABBITMQ.md).

| Метод | Маршрут | Вхід / результат |
| --- | --- | --- |
| POST | `/api/analysis/image` | multipart `file`, JPG/JPEG/PNG до 20 МБ; 202 AcceptedAnalysis |
| POST | `/api/analysis/audio` | multipart `file`, WAV/MP3/FLAC/M4A/AAC/OGG до 50 МБ, 0,25–60 с; 202 AcceptedAnalysis |
| POST | `/api/analysis/batch` | multipart повторювані `files`, 1–15 фотографій; 202 AcceptedBatchItem[] |
| GET | `/api/analyses/{UUID}/status` | AnalysisStatus: стан, дати, retryCount, помилка, результат |
| POST | `/api/analysis/sync/{image або audio}` | Явна синхронна сумісність; 201 Analysis |
| GET | `/api/analyses` | сторінка історії завершених аналізів |
| GET | `/api/analyses/{id}` | Analysis із TOP-3 та Bird |
| DELETE | `/api/analyses/{id}` | видалення запису та його серверної копії, 204 |
| GET | `/api/analyses/{id}/file` | медіа, MIME, `nosniff`, підтримка Range для аудіо |
| GET | `/api/analyses/compare?firstId=1&secondId=16` | два результати й серверний висновок про таксони |
| GET | `/api/birds` | довідник SQL, до 500 видів |
| GET | `/api/birds/{id}` | картка виду |
| GET | `/api/birds/search?search=кардинал` | пошук за українською/англійською/науковою назвою або родиною |
| GET | `/api/birds/compare?firstId=1&secondId=2` | first, second |
| GET | `/api/statistics/summary` | totalAnalyses, imageAnalyses, audioAnalyses, identifiedSpecies, averageConfidence, minConfidence, maxConfidence, labelledEvaluations |
| GET | `/api/statistics/species` | до 30 класів, count, averageConfidence |
| GET | `/api/statistics/confidence` | 4 bins: [0;0,25), [0,25;0,5), [0,5;0,75), [0,75;1] |
| GET | `/api/statistics/evaluations` | samples, top1Correct, top3Correct, model, experiment тільки для еталонів |
| GET | `/api/export/csv` | UTF-8 BOM, Content-Disposition bird_analysis.csv |
| GET | `/api/health` | 200 ok або 503 degraded із central/database/ai/rabbitmq/worker/resultConsumer |

## Історія

Параметри: `page=1`, `pageSize=20` (1–100), `search=`, `analysisType=image|audio`, `sort=date_desc|date_asc|confidence_desc|species`. Порожній `analysisType` означає всі типи. Приклад: `/api/analyses?page=2&pageSize=15&search=Cardinal&sort=confidence_desc`.

Пошук і сортування виконуються у SQL через EF, а не фільтруванням локальної історії телефона. Пошук включає файл, клас моделі та назви пов’язаного птаха. Відповідь: `{ items: Analysis[], total: number, page: number, pageSize: number }`. Усі впорядкування мають додатковий порядок за ID для стабільних сторінок.

## Analysis

Поля контракту: `analysisId` (UUID), `status`, `id` (числовий), `analysisType`, `originalFileName`, `fileUrl`, `predictedSpecies`, `confidence`, `modelName`, `modelRevision`, `analysisDate`, `description`, `elapsedSeconds`, `bird`, `predictions`, `evaluation`.

Для Completed `predictions`: рівно 3 записи `{ speciesName, scientificName, confidence, rank }`; rank 1–3. `bird` та `scientificName` можуть бути null, якщо локальний перевірений довідник не має надійного зіставлення. `evaluation` є лише для імпортованих розмічених результатів. `fileUrl` є відносним маршрутом **центрального** API. Шлях до диска, SQLite ID та connection string клієнтам не видаються.

AcceptedAnalysis: `{ analysisId: UUID, status: "Pending" | "Queued", statusUrl, historyId: number }`. Pending означає зафіксований SQL Outbox, Queued — підтверджену публікацію брокером. HTTP 202 повертається без очікування моделі.

AcceptedBatchItem: `{ fileName, task: AcceptedAnalysis | null, error: string | null }`. Кожне прийняте фото має власний statusUrl. Прийняття файлів послідовне, їх inference виконує worker. Збій БД після частини пакета може залишити вже прийняті завдання в Outbox; перед повторною відправкою перевірте історію.

AnalysisStatus: `{ analysisId, historyId, analysisType, status, createdAt, startedAt, completedAt, errorMessage, retryCount, correlationId, stalled, result }`. Стани: Pending, Queued, Processing, Completed, Failed. `result` існує лише для Completed. Вміст пошкодженого файла дає Failed асинхронно; некоректне розширення або розмір відхиляються до постановки в чергу. Видалення незавершеної задачі дає 409.

Час: ISO 8601 із часовим зсувом. Confidence: число 0–1; показ відсотка — лише форматування.

## Помилки

ASP.NET повертає ProblemDetails із `status`, `title`, `detail`, `traceId` або стандартний validation problem для відсутніх multipart-полів. Типові коди: 400 — параметри, 404 — запис/файл, 413 — розмір, 422 — формат, у sync також пошкоджений вміст; пошкоджений async-файл переходить у Failed, 502 — недоступний AI або некоректний контракт, 503 — SQL недоступний або degraded health, 504 — AI timeout. Деталі SQL та секрети не потрапляють у відповіді. Журнал містить ідентифікатор запиту.

Ліміти: фото 20 МБ, аудіо 50 МБ, весь центральний multipart-запит 320 МБ, AI-запит 51 МБ. Ліміт фото в пікселях — 25 млн. Аудіо ресемплюється до очікуваної частоти моделі. Таймаут ASP.NET → AI налаштовується `AiServer__TimeoutSeconds` (180 за замовчуванням). Автоматичних повторів POST немає, щоб не створювати дублікати після невідомого результату.

## Приватний AI API

`GET /health`, `POST /predict/image`, `POST /predict/audio`. Multipart поле `file`. Request body документується FastAPI у `/docs`; відповіді описані Pydantic. CORS для клієнтів не вмикається. При заданому `AI_INTERNAL_KEY` обов’язковий `X-AI-Key`, включно з health.

Успіх: `analysis_type`, `model_id`, `model_revision`, `elapsed_seconds`, `predictions[]` (`species_name`, `scientific_name`, `confidence`, `rank`), `metadata`. Помилка: `code`, `message`, `request_id`. ASP.NET перевіряє тип аналізу, скінченні значення score/часу, кількість і ранги TOP-3, порядок confidence, відсутність повторених класів і явного `mock_used: true`. Production-код не має mock-fallback.

## Налаштування

`ConnectionStrings__BirdLab`, `AiServer__BaseUrl`, `AiServer__TimeoutSeconds`, `AiServer__InternalKey`, `Storage__Root`, `CatalogPath`, `Cors__Origins__0` та наступні елементи. Для Python: `BIRD_OFFLINE`, `BIRD_DEVICE`, `BIRD_MODEL_CACHE`, `AI_INTERNAL_KEY`. Для брокера: `RabbitMQ__Host`, `RabbitMQ__Port`, `RabbitMQ__Username`, `RabbitMQ__Password`; у Compose значення беруться з `.env`. Для вебу: `VITE_API_URL`, `VITE_POLL_INTERVAL_MS`. Для Expo: `EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_POLL_INTERVAL_MS`. SQL та AI-секрети не є публічними frontend environment variables.
