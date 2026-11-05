# AI Bird Lab

Навчальний застосунок для визначення птахів за фото й аудіо. Наявна система поєднує Streamlit, FastAPI/Hugging Face, ASP.NET Core/MS SQL, RabbitMQ/Python Worker, React/Vite, Expo Go та тестові криптовалютні підписки Solidity/Foundry.

SQL є джерелом істини для центрального API; RabbitMQ доставляє завдання та результати через Outbox/Inbox. Клієнти звертаються до ASP.NET API. Передплата оплачується вручну; mainnet вимкнено. Типова конфігурація Base Sepolia не приймає платежі до окремого налаштування контракту власником.

## Вміст репозиторію

- `birdlab/`, `app.py`: початковий Streamlit та спільна Python-логіка.
- `ai-server/`: FastAPI, справжні моделі та RabbitMQ Worker.
- `central-server/`, `central-server.Tests/`: API, Identity, EF Core migrations, підписки й тести.
- `web-app/`, `mobile-app/`, `shared/`: веб, Expo Go та спільні типи/API.
- `contracts/`: Solidity, Foundry та скрипти тестового розгортання.
- `rabbitmq/`, `compose*.yaml`: брокер і локальне серверне оточення.
- `tests/`, `scripts/`: Python-тести та відтворювані перевірки.
- `data/birds.json`, `sample_images/`, `sample_audio/`, `sample_manifest.csv`: публічний довідник і ліцензовані тестові зразки.

Власні бази, історія, uploads, полеві нотатки, секрети, кеші, залежності, збірки та локальні протоколи перевірок залишаються поза Git. SQLite й робочі папки створюються застосунком під час використання; перенесення власної старої історії виконується окремо за [інструкцією міграції](docs/MIGRATION.md).

## Початок роботи

Потрібні Python 3.12, .NET 10, Node.js, SQL Server/Docker; для контрактів — Foundry. З кореня проєкту в PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r ai-server/requirements.txt
.\.venv\Scripts\python.exe scripts/setup_env.py
.\.venv\Scripts\python.exe scripts/download_models.py
dotnet restore central-server
dotnet restore central-server.Tests
npm --prefix web-app ci
npm --prefix mobile-app ci
npm --prefix contracts ci
docker compose up -d --build
```

`scripts/setup_env.py` створює локальні випадкові секрети, не друкуючи їхніх значень. Публічні параметри задавайте за `.env.example`; файли `.env` не публікуйте. Клієнти мають власні `.env.example`. Expo потребує LAN-адреси центрального API для фізичного телефона.

```powershell
npm --prefix web-app run dev
npm --prefix mobile-app start
```

Початковий Streamlit: `.\.venv\Scripts\python.exe -m streamlit run app.py`. Docker і Streamlit мають незалежне сховище даних. Наявні Docker volumes та локальні бази не очищайте під час оновлення.

## Перевірки й документація

- [Підписки, Anvil, Base Sepolia, API та команди запуску](docs/SUBSCRIPTIONS.md).
- [Архітектура RabbitMQ](docs/RABBITMQ.md), [API](docs/API.md), [Expo/iPhone](docs/IPHONE.md).
- [Підготовка до GitHub і правила конфіденційності](docs/GITHUB_PREPARATION.md).
- [Точний перелік файлів першого коміту](docs/GIT_COMMIT_FILES.md).

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.test-artifacts/pytest-git
.\scripts\test_subscriptions.ps1 -Sql
npm --prefix web-app test
npm --prefix web-app run build
npm --prefix mobile-app run typecheck
cd contracts
forge test
```

Історичні документи в `docs/` можуть посилатися на локальну `verification/`: ці протоколи й знімки залишені на машині та не входять до Git. Тести реального SQL, моделей, Docker, пристрою та блокчейна потребують відповідного оточення; модульний тест або експорт iOS не є доказом фізичного iPhone. Платіжна система не проходила незалежного аудиту.
