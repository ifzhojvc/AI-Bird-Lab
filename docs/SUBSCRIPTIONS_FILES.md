# Файли розширення підписок

Повна структура вихідного комплекту без залежностей, кешів, збірок, секретів і копій submission. Наявні робочі storage, SQL, uploads і моделі не очищалися; бінарні результати центрального сервера не входять до вихідного комплекту.

## Структура

```text
Birds/
├── .streamlit/
│   └── config.toml
├── ai-server/
│   ├── ai_api/
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── audio.py
│   │   └── schemas.py
│   ├── bird_worker/
│   │   ├── __init__.py
│   │   ├── contracts.py
│   │   ├── inference.py
│   │   ├── runtime.py
│   │   └── storage.py
│   ├── .env.example
│   ├── Dockerfile
│   ├── main.py
│   ├── replay_results.py
│   ├── requirements-lock.txt
│   ├── requirements.txt
│   └── worker.py
├── birdlab/
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── analysis.py
│   │   ├── common.py
│   │   ├── library.py
│   │   └── overview.py
│   ├── __init__.py
│   ├── config.py
│   ├── domain.py
│   ├── errors.py
│   ├── export.py
│   ├── files.py
│   ├── models.py
│   ├── reference.py
│   ├── repository.py
│   ├── service.py
│   ├── statistics.py
│   └── taxonomy.py
├── central-server/
│   ├── Auth/
│   │   └── SessionAuthentication.cs
│   ├── Controllers/
│   │   ├── AnalysisController.cs
│   │   ├── AuthController.cs
│   │   ├── BirdsController.cs
│   │   ├── LegacyArchiveController.cs
│   │   ├── StatisticsController.cs
│   │   ├── SubscriptionsController.cs
│   │   └── WalletsController.cs
│   ├── Data/
│   │   ├── BirdDbContext.cs
│   │   └── SubscriptionSchema.cs
│   ├── DTOs/
│   │   └── Contracts.cs
│   ├── Infrastructure/
│   │   ├── ApiException.cs
│   │   └── FileStore.cs
│   ├── Messaging/
│   │   ├── Events.cs
│   │   ├── OutboxDispatcher.cs
│   │   ├── RabbitBus.cs
│   │   ├── ResultConsumer.cs
│   │   ├── ResultProcessor.cs
│   │   └── StalledJobMonitor.cs
│   ├── Migrations/
│   │   ├── 20261028115223_InitialCreate.cs
│   │   ├── 20261028115223_InitialCreate.Designer.cs
│   │   ├── 20261029165845_AsyncMessaging.cs
│   │   ├── 20261029165845_AsyncMessaging.Designer.cs
│   │   ├── 20261103154944_CryptoSubscriptions.cs
│   │   ├── 20261103154944_CryptoSubscriptions.Designer.cs
│   │   └── BirdDbContextModelSnapshot.cs
│   ├── Models/
│   │   ├── Analysis.cs
│   │   ├── Bird.cs
│   │   ├── Messaging.cs
│   │   └── Subscriptions.cs
│   ├── Properties/
│   │   └── launchSettings.json
│   ├── Services/
│   │   ├── AiClient.cs
│   │   ├── AnalysisService.cs
│   │   ├── CatalogSeeder.cs
│   │   ├── CsvExport.cs
│   │   ├── LegacyImporter.cs
│   │   └── StatisticsService.cs
│   ├── Subscriptions/
│   │   ├── BlockchainOptions.cs
│   │   ├── BlockchainVerifier.cs
│   │   ├── PaymentService.cs
│   │   ├── SubscriptionMonitor.cs
│   │   ├── SubscriptionService.cs
│   │   ├── UserLock.cs
│   │   └── WalletService.cs
│   ├── appsettings.json
│   ├── BirdLab.Api.csproj
│   ├── Dockerfile
│   └── Program.cs
├── central-server.Tests/
│   ├── ApiTests.cs
│   ├── BirdLab.Api.Tests.csproj
│   ├── MessagingTests.cs
│   ├── SqlMessagingTests.cs
│   ├── SqlSubscriptionTests.cs
│   ├── SubscriptionApiTests.cs
│   ├── SubscriptionTests.cs
│   └── TestAccount.cs
├── contracts/
│   ├── script/
│   │   ├── DeployBaseSepolia.s.sol
│   │   └── DeployLocal.s.sol
│   ├── src/
│   │   ├── BirdLabSubscriptions.sol
│   │   └── MockUSDC.sol
│   ├── test/
│   │   └── BirdLabSubscriptions.t.sol
│   ├── foundry.toml
│   ├── package-lock.json
│   └── package.json
├── data/
│   ├── birds.json
│   ├── field_notes.json
│   └── submission_uploads.json
├── docs/
│   ├── API.md
│   ├── CHANGES.md
│   ├── IPHONE.md
│   ├── LEGACY_REPORT.md
│   ├── MIGRATION.md
│   ├── RABBITMQ.md
│   ├── RABBITMQ_CHANGES.md
│   ├── RABBITMQ_VERIFICATION.md
│   ├── SUBSCRIPTIONS.md
│   ├── SUBSCRIPTIONS_FILES.md
│   ├── SUBSCRIPTIONS_VERIFICATION.md
│   └── VERIFICATION.md
├── mobile-app/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Common.tsx
│   │   │   └── TaskStatus.tsx
│   │   ├── screens/
│   │   │   ├── Account.tsx
│   │   │   ├── Capture.tsx
│   │   │   ├── Compare.tsx
│   │   │   ├── Details.tsx
│   │   │   ├── History.tsx
│   │   │   ├── Home.tsx
│   │   │   ├── Info.tsx
│   │   │   └── Statistics.tsx
│   │   ├── api.ts
│   │   ├── auth.tsx
│   │   ├── navigation.ts
│   │   ├── theme.ts
│   │   └── useAnalysisTask.ts
│   ├── .env.example
│   ├── app.json
│   ├── App.tsx
│   ├── index.ts
│   ├── metro.config.js
│   ├── package-lock.json
│   ├── package.json
│   └── tsconfig.json
├── rabbitmq/
│   ├── bootstrap.sh
│   ├── definitions.json
│   └── rabbitmq.conf
├── sample_audio/
│   ├── LICENSE.txt
│   ├── manifest.json
│   ├── robin.wav
│   └── robin_original.ogg
├── sample_images/
│   ├── 01_Cardinalis_cardinalis.jpg
│   ├── 02_Cyanocitta_cristata.jpg
│   ├── 03_Spinus_tristis.jpg
│   ├── 04_Carduelis_carduelis.jpg
│   ├── 05_Passerina_cyanea.jpg
│   ├── 06_Passerina_ciris.jpg
│   ├── 07_Agelaius_phoeniceus.png
│   ├── 08_Anas_platyrhynchos.jpg
│   ├── 09_Passer_domesticus.jpg
│   ├── 10_Hirundo_rustica.jpg
│   ├── 11_Icterus_galbula.jpg
│   ├── 12_Bombycilla_cedrorum.jpg
│   ├── 13_Dryocopus_pileatus.jpg
│   ├── 14_Pelecanus_occidentalis.jpg
│   └── 15_Halcyon_smyrnensis.jpg
├── scripts/
│   ├── build_report.py
│   ├── build_subscription_delivery_docs.py
│   ├── check_delivery.py
│   ├── check_ports.ps1
│   ├── check_subscription_delivery.py
│   ├── configure_mobile_lan.ps1
│   ├── download_audio_sample.py
│   ├── download_models.py
│   ├── download_samples.py
│   ├── final_check.py
│   ├── local_blockchain.py
│   ├── prepare_submission.py
│   ├── rabbitmq_admin.py
│   ├── research_sources.py
│   ├── restore_uploads.py
│   ├── run_ai_local.ps1
│   ├── run_central_local.ps1
│   ├── run_worker_local.ps1
│   ├── select_image_model.py
│   ├── setup_env.py
│   ├── snapshot_legacy.py
│   ├── subscription_baseline.py
│   ├── subscription_data.py
│   ├── test_subscriptions.ps1
│   ├── verify_ai_outage.py
│   ├── verify_client_server.py
│   ├── verify_final.py
│   ├── verify_mobile_protocol.py
│   ├── verify_rabbitmq.py
│   ├── verify_real.py
│   ├── verify_submission.py
│   └── verify_subscriptions.py
├── shared/
│   ├── api.ts
│   ├── contracts.ts
│   ├── polling.ts
│   └── subscriptions.ts
├── tests/
│   ├── conftest.py
│   ├── test_ai_api.py
│   ├── test_export_statistics.py
│   ├── test_files.py
│   ├── test_integration_real.py
│   ├── test_models_taxonomy.py
│   ├── test_repository.py
│   ├── test_service_reference.py
│   ├── test_submission_restore.py
│   ├── test_ui.py
│   └── test_worker.py
├── uploads/
│   ├── 114ff3ff8639418f92e03f4e05609cc0.jpg
│   ├── 29c8ff748bf44d099f50cd1624c9a35c.jpg
│   ├── 3d5178c6c28145ca93c6992dc88b8258.jpg
│   ├── 3dbd54d4a65d450a8e92a2f8658efb7a.jpg
│   ├── 56151d217d1345438fac31ab654cca05.jpg
│   ├── 5df4dd1021b648f39f79f70f93b35e8b.jpg
│   ├── 7edc8f56acd448099cb34595a3541ff9.jpg
│   ├── 9a98291deb8b476e8f99b635dc87c400.jpg
│   ├── ae8f4ed4f01b4bef81f0479b35e9a4ea.png
│   ├── b0b58b2f12244eb8baa9ce76becb5cd4.jpg
│   ├── ce1c0e97debf45acb46cba29bede21b9.wav
│   ├── dfe8448cb5e64cadacd9c00f3744c84f.jpg
│   ├── e240516056834a8f8fc4e7cbbd915f2b.jpg
│   ├── e3be5b91f02a4c9894dcc9eb9a7fc040.jpg
│   ├── e523387a9ff1490389d7244e2a8d531e.jpg
│   └── ee50bce80593458ca658366c375b4638.jpg
├── verification/
│   ├── rabbitmq-screenshots/
│   │   ├── management-queues.jpg
│   │   ├── web-audio-completed.jpg
│   │   ├── web-completed.jpg
│   │   ├── web-processing.jpg
│   │   └── web-queued.jpg
│   ├── screenshots/
│   │   ├── audio-browser-result.jpg
│   │   ├── compare-browser.jpg
│   │   ├── gallery-desktop.jpg
│   │   ├── home-desktop.jpg
│   │   ├── home-mobile.jpg
│   │   ├── photo-browser-result.jpg
│   │   ├── statistics-desktop.jpg
│   │   ├── web-client-compare.png
│   │   ├── web-client-desktop.png
│   │   ├── web-client-phone.png
│   │   ├── web-client-real-audio.png
│   │   └── web-client-real-photo.png
│   ├── sources/
│   │   ├── audio_config.json
│   │   ├── audio_metadata.json
│   │   ├── audio_preprocessor_config.json
│   │   ├── audio_README.md
│   │   ├── audio_tensor_shapes.json
│   │   ├── image_config.json
│   │   ├── image_metadata.json
│   │   ├── image_preprocessor_config.json
│   │   ├── image_README.md
│   │   ├── image_tensor_shapes.json
│   │   ├── selected_image_config.json
│   │   ├── selected_image_metadata.json
│   │   ├── selected_image_preprocessor_config.json
│   │   ├── selected_image_README.md
│   │   ├── selected_image_tensor_shapes.json
│   │   └── wikimedia_probe.json
│   ├── subscription-screenshots/
│   │   ├── login.png
│   │   └── plans-desktop.png
│   ├── ai-api-tests.xml
│   ├── ai-outage.json
│   ├── browser_checks.json
│   ├── central-server-tests.trx
│   ├── client-server-baseline.json
│   ├── client-server-real.json
│   ├── delivery-check.json
│   ├── expo-validation.json
│   ├── final-api-check.json
│   ├── final_checks.json
│   ├── integration-tests.xml
│   ├── legacy-regression.xml
│   ├── local-deployment.json
│   ├── migration-first.json
│   ├── migration-repeat.json
│   ├── mobile-protocol.json
│   ├── python-complete.xml
│   ├── rabbitmq-browser.json
│   ├── rabbitmq-changes.json
│   ├── rabbitmq-final-logs.txt
│   ├── rabbitmq-final.json
│   ├── rabbitmq-integration.json
│   ├── rabbitmq-migration.json
│   ├── rabbitmq-python.xml
│   ├── rabbitmq-replay.json
│   ├── rabbitmq-sql.trx
│   ├── rabbitmq-submission-roundtrip.json
│   ├── rabbitmq-sync-compat.json
│   ├── rabbitmq-unit.trx
│   ├── real_run.json
│   ├── sample_download.json
│   ├── submission-roundtrip.json
│   ├── submission-size.json
│   ├── subscriptions-blockchain.json
│   ├── subscriptions-browser.json
│   ├── subscriptions-changes.json
│   ├── subscriptions-client-validation.json
│   ├── subscriptions-delivery-check.json
│   ├── subscriptions-docker.json
│   ├── subscriptions-final.json
│   ├── subscriptions-foundry.json
│   ├── subscriptions-integration.json
│   ├── subscriptions-preservation.json
│   ├── subscriptions-python.xml
│   ├── subscriptions-sql.trx
│   ├── unit-tests.xml
│   └── worker-unit.xml
├── web-app/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AnalysisTask.tsx
│   │   │   └── Common.tsx
│   │   ├── pages/
│   │   │   ├── Account.tsx
│   │   │   ├── Analyze.tsx
│   │   │   ├── Checkout.tsx
│   │   │   ├── Compare.tsx
│   │   │   ├── History.tsx
│   │   │   ├── Home.tsx
│   │   │   ├── Statistics.tsx
│   │   │   └── Subscriptions.test.tsx
│   │   ├── api.test.ts
│   │   ├── api.ts
│   │   ├── App.tsx
│   │   ├── auth.tsx
│   │   ├── main.tsx
│   │   ├── polling.test.ts
│   │   ├── styles.css
│   │   └── web3.ts
│   ├── .env.example
│   ├── index.html
│   ├── package-lock.json
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── .dockerignore
├── .env.example
├── .gitignore
├── app.py
├── bird_analysis.csv
├── birds.db
├── compose.local.yaml
├── compose.subscriptions-test.yaml
├── compose.yaml
├── global.json
├── pytest.ini
├── README.md
├── report.md
├── requirements-lock.txt
├── requirements.txt
└── sample_manifest.csv
```

## Створені файли

- `central-server.Tests/SqlSubscriptionTests.cs`
- `central-server.Tests/SubscriptionApiTests.cs`
- `central-server.Tests/SubscriptionTests.cs`
- `central-server.Tests/TestAccount.cs`
- `central-server/Auth/SessionAuthentication.cs`
- `central-server/Controllers/AuthController.cs`
- `central-server/Controllers/LegacyArchiveController.cs`
- `central-server/Controllers/SubscriptionsController.cs`
- `central-server/Controllers/WalletsController.cs`
- `central-server/Data/SubscriptionSchema.cs`
- `central-server/Migrations/20261103154944_CryptoSubscriptions.Designer.cs`
- `central-server/Migrations/20261103154944_CryptoSubscriptions.cs`
- `central-server/Models/Subscriptions.cs`
- `central-server/Subscriptions/BlockchainOptions.cs`
- `central-server/Subscriptions/BlockchainVerifier.cs`
- `central-server/Subscriptions/PaymentService.cs`
- `central-server/Subscriptions/SubscriptionMonitor.cs`
- `central-server/Subscriptions/SubscriptionService.cs`
- `central-server/Subscriptions/UserLock.cs`
- `central-server/Subscriptions/WalletService.cs`
- `compose.local.yaml`
- `compose.subscriptions-test.yaml`
- `contracts/foundry.toml`
- `contracts/package-lock.json`
- `contracts/package.json`
- `contracts/script/DeployBaseSepolia.s.sol`
- `contracts/script/DeployLocal.s.sol`
- `contracts/src/BirdLabSubscriptions.sol`
- `contracts/src/MockUSDC.sol`
- `contracts/test/BirdLabSubscriptions.t.sol`
- `docs/SUBSCRIPTIONS.md`
- `docs/SUBSCRIPTIONS_FILES.md`
- `docs/SUBSCRIPTIONS_VERIFICATION.md`
- `mobile-app/src/auth.tsx`
- `mobile-app/src/screens/Account.tsx`
- `scripts/build_subscription_delivery_docs.py`
- `scripts/check_subscription_delivery.py`
- `scripts/local_blockchain.py`
- `scripts/run_ai_local.ps1`
- `scripts/run_central_local.ps1`
- `scripts/run_worker_local.ps1`
- `scripts/subscription_data.py`
- `scripts/test_subscriptions.ps1`
- `scripts/verify_subscriptions.py`
- `shared/subscriptions.ts`
- `verification/local-deployment.json`
- `verification/subscription-screenshots/login.png`
- `verification/subscription-screenshots/plans-desktop.png`
- `verification/subscriptions-blockchain.json`
- `verification/subscriptions-browser.json`
- `verification/subscriptions-changes.json`
- `verification/subscriptions-client-validation.json`
- `verification/subscriptions-delivery-check.json`
- `verification/subscriptions-docker.json`
- `verification/subscriptions-final.json`
- `verification/subscriptions-foundry.json`
- `verification/subscriptions-integration.json`
- `verification/subscriptions-preservation.json`
- `verification/subscriptions-python.xml`
- `verification/subscriptions-sql.trx`
- `web-app/src/auth.tsx`
- `web-app/src/pages/Account.tsx`
- `web-app/src/pages/Checkout.tsx`
- `web-app/src/pages/Subscriptions.test.tsx`
- `web-app/src/web3.ts`

## Змінені файли

- `.dockerignore`
- `.env.example`
- `.gitignore`
- `README.md`
- `ai-server/bird_worker/runtime.py`
- `central-server.Tests/ApiTests.cs`
- `central-server.Tests/BirdLab.Api.Tests.csproj`
- `central-server.Tests/MessagingTests.cs`
- `central-server.Tests/SqlMessagingTests.cs`
- `central-server/BirdLab.Api.csproj`
- `central-server/Controllers/AnalysisController.cs`
- `central-server/Controllers/BirdsController.cs`
- `central-server/Controllers/StatisticsController.cs`
- `central-server/Data/BirdDbContext.cs`
- `central-server/Messaging/OutboxDispatcher.cs`
- `central-server/Messaging/RabbitBus.cs`
- `central-server/Messaging/ResultProcessor.cs`
- `central-server/Migrations/BirdDbContextModelSnapshot.cs`
- `central-server/Models/Analysis.cs`
- `central-server/Program.cs`
- `central-server/Services/AnalysisService.cs`
- `central-server/Services/StatisticsService.cs`
- `central-server/appsettings.json`
- `compose.yaml`
- `docs/API.md`
- `docs/IPHONE.md`
- `mobile-app/App.tsx`
- `mobile-app/app.json`
- `mobile-app/package-lock.json`
- `mobile-app/package.json`
- `mobile-app/src/components/Common.tsx`
- `mobile-app/src/navigation.ts`
- `mobile-app/src/screens/Details.tsx`
- `mobile-app/src/screens/History.tsx`
- `mobile-app/src/screens/Info.tsx`
- `mobile-app/src/screens/Statistics.tsx`
- `rabbitmq/bootstrap.sh`
- `report.md`
- `scripts/prepare_submission.py`
- `shared/api.ts`
- `verification/submission-roundtrip.json`
- `verification/submission-size.json`
- `web-app/package-lock.json`
- `web-app/package.json`
- `web-app/src/App.tsx`
- `web-app/src/api.ts`
- `web-app/src/main.tsx`
- `web-app/src/pages/Analyze.tsx`
- `web-app/src/pages/History.tsx`
- `web-app/src/pages/Statistics.tsx`
- `web-app/src/styles.css`

Порівняння зроблено з контрольним інвентарем до розширення. Список включає документацію та докази перевірок. Жоден попередній файл основного проєкту не видалено.
