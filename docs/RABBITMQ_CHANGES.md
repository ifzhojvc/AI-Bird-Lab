# Файли RabbitMQ-інтеграції

Дата: 29.10.2026. Змінено основний проєкт; `submission` не редагувалася.

## Оновлена структура

```text
Birds/
  compose.yaml
  .env.example
  rabbitmq/                  broker config, bootstrap, policies
  central-server/
    Messaging/               publisher, outbox, consumer, contracts, diagnostics
    Models/                  existing Analysis + Outbox/Inbox
    Migrations/              InitialCreate + AsyncMessaging + snapshot
    Controllers/             async 202 + status; existing history/statistics
  ai-server/
    worker.py
    replay_results.py
    bird_worker/             contracts, media/ledger, inference adapter, runtime
    ai_api/                  existing FastAPI and audio decoder
  shared/                    contracts, HTTP client, lifecycle polling
  web-app/src/               existing React + AnalysisTask
  mobile-app/src/            existing Expo + useAnalysisTask/TaskStatus
  central-server.Tests/      existing tests + messaging/SQL tests
  tests/test_worker.py
  scripts/                   startup, submission, real RabbitMQ protocol
  docs/                      architecture, API, report evidence, file lists
  verification/              JSON/TRX/XML and browser screenshots
  README.md
  report.md
```

## Створено

- `README.md`
- `ai-server/bird_worker/__init__.py`
- `ai-server/bird_worker/contracts.py`
- `ai-server/bird_worker/inference.py`
- `ai-server/bird_worker/runtime.py`
- `ai-server/bird_worker/storage.py`
- `ai-server/replay_results.py`
- `ai-server/worker.py`
- `central-server.Tests/MessagingTests.cs`
- `central-server.Tests/SqlMessagingTests.cs`
- `central-server/Messaging/Events.cs`
- `central-server/Messaging/OutboxDispatcher.cs`
- `central-server/Messaging/RabbitBus.cs`
- `central-server/Messaging/ResultConsumer.cs`
- `central-server/Messaging/ResultProcessor.cs`
- `central-server/Messaging/StalledJobMonitor.cs`
- `central-server/Migrations/20261029165845_AsyncMessaging.Designer.cs`
- `central-server/Migrations/20261029165845_AsyncMessaging.cs`
- `central-server/Models/Messaging.cs`
- `docs/RABBITMQ.md`
- `docs/RABBITMQ_CHANGES.md`
- `docs/RABBITMQ_VERIFICATION.md`
- `mobile-app/src/components/TaskStatus.tsx`
- `mobile-app/src/useAnalysisTask.ts`
- `rabbitmq/bootstrap.sh`
- `rabbitmq/definitions.json`
- `rabbitmq/rabbitmq.conf`
- `report.md`
- `scripts/rabbitmq_admin.py`
- `scripts/setup_env.py`
- `scripts/verify_rabbitmq.py`
- `shared/polling.ts`
- `web-app/src/components/AnalysisTask.tsx`
- `web-app/src/polling.test.ts`

## Змінено

- `.dockerignore`
- `.env.example`
- `.gitignore`
- `ai-server/requirements-lock.txt`
- `ai-server/requirements.txt`
- `central-server.Tests/ApiTests.cs`
- `central-server/BirdLab.Api.csproj`
- `central-server/Controllers/AnalysisController.cs`
- `central-server/Controllers/StatisticsController.cs`
- `central-server/DTOs/Contracts.cs`
- `central-server/Data/BirdDbContext.cs`
- `central-server/Migrations/BirdDbContextModelSnapshot.cs`
- `central-server/Models/Analysis.cs`
- `central-server/Program.cs`
- `central-server/Services/AnalysisService.cs`
- `central-server/Services/LegacyImporter.cs`
- `central-server/Services/StatisticsService.cs`
- `central-server/appsettings.json`
- `compose.yaml`
- `docs/API.md`
- `docs/CHANGES.md`
- `docs/IPHONE.md`
- `mobile-app/.env.example`
- `mobile-app/src/components/Common.tsx`
- `mobile-app/src/screens/Capture.tsx`
- `scripts/prepare_submission.py`
- `scripts/verify_ai_outage.py`
- `scripts/verify_client_server.py`
- `scripts/verify_final.py`
- `scripts/verify_mobile_protocol.py`
- `scripts/verify_submission.py`
- `shared/api.ts`
- `shared/contracts.ts`
- `web-app/.env.example`
- `web-app/src/components/Common.tsx`
- `web-app/src/pages/Analyze.tsx`

Локальний `.env` доповнений користувачем і паролем RabbitMQ; SQL та AI-секрети збережено. Файл не включається до здачі. Новий пароль брокера був замінений після діагностичної помилки запуску, що вивела його в CLI. У поточних діагностичних скриптах секрети фільтруються.

## Нові докази

`verification/rabbitmq-python.xml`, `worker-unit.xml`, `rabbitmq-sql.trx`, `rabbitmq-integration.json`, `rabbitmq-migration.json`, `rabbitmq-replay.json`, `rabbitmq-browser.json`, `rabbitmq-sync-compat.json`, `rabbitmq-final.json`, `rabbitmq-changes.json`, `rabbitmq-submission-roundtrip.json` та `rabbitmq-screenshots/*.jpg`. `submission-size.json` і `delivery-check.json` оновлюються наявними перевірочними скриптами.

Початкові SQLite, CSV, каталог видів, 15 фотографій, аудіо, uploads і стара SQL-історія збережені. Runtime залежності, SQL/RabbitMQ volumes, worker ledger, кеш моделей, резервні копії та build output до цього переліку вихідних файлів не входять. Нових frontend-залежностей або нативних модулів Expo не додано.
