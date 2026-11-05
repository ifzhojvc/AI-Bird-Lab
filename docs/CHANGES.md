# Склад змін

## Нові компоненти

- `ai-server/main.py`, `ai-server/ai_api/{app,audio,schemas}.py`, requirements/lock, env.example, Dockerfile.
- `central-server/Program.cs`, csproj, appsettings, launchSettings.
- `central-server/Models/{Bird,Analysis}.cs` — також Prediction та Evaluation.
- `central-server/Data/BirdDbContext.cs`.
- `central-server/DTOs/Contracts.cs`.
- `central-server/Infrastructure/{ApiException,FileStore}.cs`.
- `central-server/Services/{AiClient,AnalysisService,CatalogSeeder,CsvExport,LegacyImporter,StatisticsService}.cs`.
- `central-server/Controllers/{AnalysisController,BirdsController,StatisticsController}.cs`.
- `central-server/Migrations/20261028115223_InitialCreate.cs`, Designer та `BirdDbContextModelSnapshot.cs`.
- `central-server.Tests/BirdLab.Api.Tests.csproj`, `ApiTests.cs`.
- `shared/contracts.ts`, `shared/api.ts` — контракт і транспорт обох клієнтів.
- `web-app` — Vite/TypeScript/package/lock/env, `src/{App,main,api,api.test,styles}`, `components/Common`, `pages/{Home,Analyze,History,Statistics,Compare}`.
- `mobile-app` — Expo/package/lock/app/tsconfig/metro/env, `App.tsx`, `index.ts`, `src/{api,navigation,theme}`, `components/Common`, `screens/{Home,Capture,History,Details,Statistics,Compare,Info}`.
- `tests/test_ai_api.py`, `tests/test_submission_restore.py`.
- `scripts/snapshot_legacy.py`, `prepare_submission.py`, `restore_uploads.py`, `verify_submission.py`, `configure_mobile_lan.ps1`, `check_ports.ps1`, `check_delivery.py`, `verify_client_server.py`, `verify_mobile_protocol.py`, `verify_ai_outage.py`, `verify_final.py`.
- `global.json`, `.dockerignore`, `.env.example`, `compose.yaml`.
- `README.md`, `report.md`, `docs/{API,IPHONE,MIGRATION,VERIFICATION,CHANGES,LEGACY_REPORT}.md`.
- `data/submission_uploads.json` — тільки мапа SHA-256 і шляхів точних копій.
- Нові протоколи та браузерні PNG у `verification`.

## Змінені початкові файли

| Файл | Причина |
| --- | --- |
| `birdlab/models.py` | Streamlit-кеш замінено незалежним потокобезпечним кешем з тим самим API `.clear()`; додано явний вибір CPU/CUDA. Алгоритми моделей і агрегація не переписувалися. |
| `birdlab/config.py` | Необов’язковий `BIRD_MODEL_CACHE` для локального та контейнерного кешу. |
| `scripts/build_report.py` | Старий звіт записується в `docs/LEGACY_REPORT.md`, не перезаписуючи новий звіт. |
| `.gitignore` | Додано Node/.NET/Expo/runtime/cache/submission виключення. |

## Збережено

`app.py`, усі початкові сторінки Streamlit, Repository/Service/reference/files/taxonomy, SQLite `birds.db`, `bird_analysis.csv`, `data/birds.json`, `data/field_notes.json`, `sample_manifest.csv`, усі 15 зображень, аудіо, uploads, початкові тести та протоколи. Зміни бази й CSV виконуються лише через окремі нові компоненти; новий API не перезаписує початковий CSV.

Резервні копії в `data/backups` та SQL runtime-сховище збережені локально. У комплект вихідного коду не входять відновлювані залежності, кеші й runtime-дані центрального сервера. Точні копії uploads у компактній папці замінюються маніфестом і відновлюються окремою перевіреною командою; у робочій папці нічого не видалено.


## Інтеграція RabbitMQ, 29.10.2026

Поточний перелік нових та змінених файлів: [RABBITMQ_CHANGES.md](RABBITMQ_CHANGES.md). Архітектура і протоколи: [RABBITMQ.md](RABBITMQ.md), [RABBITMQ_VERIFICATION.md](RABBITMQ_VERIFICATION.md). Попередні розділи цього документа описують базову клієнт-серверну версію від 28.10.2026.
