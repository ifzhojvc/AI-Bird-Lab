# SQLite → SQL Server

Оригінальна схема: `bird_info`, `analyses`, `predictions`, `evaluations`. Основна нова БД: `Birds`, `Analyses`, `Predictions`, `Evaluations`. Міграція EF Code First — `20261028115223_InitialCreate`, разом із Designer та ModelSnapshot.

## Відповідність

| SQLite | SQL Server |
| --- | --- |
| `bird_info.payload` і `data/birds.json` | поля `Bird`, усі URL джерел |
| `analyses.analysis_type` | `AnalysisType` |
| `original_name` | `OriginalFileName`, без шляху користувача |
| `file_path` | незалежна копія у FileStore, безпечний UUID-ключ |
| `file_hash` | SHA-256 перевірений до копіювання |
| `model_id`, `model_revision` | `ModelName`, `ModelRevision` |
| `analysis_date` | `DateTimeOffset`, збережено UTC і сам момент часу |
| `bird_snapshot`, `metadata` | `BirdSnapshotJson`, `MetadataJson` |
| `predictions` | TOP-3, назва, таксон, score, rank |
| `evaluations` | еталон, джерело мітки, hash, TOP-1/TOP-3, experiment |

## Алгоритм

1. SQLite відкривається в read-only; Backup API створює узгоджену копію навіть за наявності WAL. Доцільно завершити запис у Streamlit перед перенесенням, щоб чітко визначити межу міграції.
2. Копіюються CSV та всі медіа, на які посилається snapshot. Шляхи обмежено початковою папкою `uploads`. SHA-256 має збігатися з базою.
3. У `data/backups/migration-<UTC>` зберігаються `manifest.json` і після успіху `result.json`.
4. Каталог видів заповнюється з початкового довідника; відсутні у ньому `bird_info` додаються з SQLite. Наявні записи каталогу не перезаписуються. Точний початковий bird snapshot залишається в кожному мігрованому аналізі.
5. У транзакції створюються аналізи, передбачення та оцінки. Медійні UUID-копії незалежні від початкових файлів; при помилці транзакції нові копії прибираються.
6. Унікальний індекс `(LegacySource, LegacyId)` запобігає дублікатам. `LegacySource` — SHA-256 нормалізованого абсолютного шляху вихідної SQLite. При повторному запуску використовуйте той самий оригінальний шлях; імпорт з іншої папки вважається іншим джерелом.
7. Перед commit кількості аналізів, TOP-3 і оцінок для джерела порівнюються з SQLite. Невідповідність скасовує перенесення.

Імпорт є додаванням нових legacy ID. Редагування або видалення вже імпортованих рядків у старій SQLite не синхронізує SQL автоматично. Ведіть нову історію через ASP.NET; збережений Streamlit використовуйте для відтворення попередньої роботи. Не переміщуйте SQLite під час повторного імпорту й не називайте двонапрямною синхронізацією цю одноразову міграцію.

## Команди

```powershell
.\.venv\Scripts\python.exe scripts/restore_uploads.py
dotnet run --project central-server -- --import-sqlite 'C:\ITSTEP\AI\Birds\birds.db'
dotnet run --project central-server --no-build -- --import-sqlite 'C:\ITSTEP\AI\Birds\birds.db'
```

Повторний запуск створює нову резервну копію для аудиту, але не нові аналізи.

Для керування міграціями встановіть/відновіть `dotnet-ef` 10.0.14 та використовуйте `dotnet ef migrations list --project central-server`, `dotnet ef migrations script --idempotent --project central-server` або `dotnet ef database update --project central-server`. Нормальний імпорт і `--migrate-db` уже викликають `MigrateAsync`, тому CLI EF не потрібен користувачу для запуску.

## Контейнерний імпорт

Compose `migrate` застосовує схему й довідник до окремої контейнерної SQL-бази. Автоматичного перенесення Windows-шляхів немає. Щоб імпортувати ту саму історію, підготуйте **копію** `birds.db`, `bird_analysis.csv`, `uploads/` в одній папці, змонтуйте її read/write в `/legacy` (для backups) у разовий контейнер `central`, збережіть його connection string і volume `/app/storage`, та запустіть:

```powershell
docker compose run --rm -v "${PWD}:/legacy" central --import-sqlite /legacy/birds.db
```

Спочатку відновіть uploads у компактній копії. Для послідовних повторів у Docker використовуйте той самий шлях `/legacy/birds.db`. Перенесення з абсолютного Windows-шляху і з `/legacy` в одну й ту саму БД вважається двома джерелами: не змішуйте їх. На поточному ПК Docker daemon не був запущений, тому контейнерний варіант документований, але не перевірений.

## Фактична перевірка

Перший запуск: 16 додано, 48 передбачень, 15 оцінок. Повторний: 0 додано, 16 пропущено, 48 передбачень і 15 оцінок. Оригінальні SQLite/CSV/uploads/зразки звірено з `verification/client-server-baseline.json` за SHA-256. Оригінали збережено, нові SQL-аналізи додаються в незалежну історію.
