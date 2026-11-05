# Перевірка RabbitMQ-інтеграції

Дата: **29.10.2026**. Робота та перевірка виконані в основному проєкті на Windows із Docker Desktop Linux containers. Застосовувалися справжні RabbitMQ 4.4.0, MS SQL Server, ASP.NET Core, Python Worker та кешовані/завантажені Hugging Face моделі. Фізичний iPhone не підключався.

## Автоматичні тести та збірки

| Перевірка | Фактичний результат | Доказ |
| --- | --- | --- |
| Увесь Python-набір із `RUN_REAL_MODELS=1` | **129 passed**, один відомий Starlette/anyio deprecation warning | `verification/rabbitmq-python.xml` |
| Worker unit-тести | **14 passed**; це підміненi transport/inference, а не реальний брокер | `verification/worker-unit.xml` |
| .NET, включно з SQL integration | **38 passed, 0 skipped** | `verification/rabbitmq-sql.trx` |
| Окремі SQL integration-сценарії | Справжній SQL Express, окремі тимчасові бази: міграція старого запису та TOP-3; атомарний відкат Analysis/Outbox; Inbox-дедуплікація | `central-server.Tests/SqlMessagingTests.cs` і TRX |
| Спільний HTTP-клієнт та polling | **10 passed**: стани, скасування fetch, inactive screen, припинення після terminal/404 | `web-app/src/api.test.ts`, `polling.test.ts` |
| React production build | Успішно, 2332 modules | `npm run build --prefix web-app` |
| React та Expo TypeScript | Успішно | `npm run typecheck` у відповідних папках |
| Expo dependency check | Dependencies are up to date | `npx expo install --check` |
| expo-doctor | **21/21 passed** | Фактичний CLI-запуск поза мережевим sandbox |
| iOS JS export | Успішно, **969 modules**, `--no-bytecode` | `mobile-app/.test-artifacts/rabbitmq-ios` |
| Docker build і Compose | Образи зібрані, сервіси реально запускалися | `docker compose up -d --build`, `ps`, робочі логи |

129 Python-тестів включають попередні unit/UI/API тести, три реальні локальні integration-тести та 14 нових worker unit-тестів. .NET-набір включає InMemory/HTTP mocks для ізольованої логіки та два окремі справжні SQL integration-тести. Unit-результати не подаються як доказ реального RabbitMQ.

## Справжній прохід і відмови

`verification/rabbitmq-integration.json` містить **14 успішних груп перевірок**, `success=true`, `mock_used=false`. Кожна група має конкретні ID, статуси, SQL-лічильники або literal AI output.

1. Авторизований Management API підтвердив RabbitMQ **4.4.0**, дев’ять durable quorum queues та policies.
2. При зупиненому worker HTTP 202 створив SQL Analysis і Outbox. Після confirm було встановлено PublishedAt та Queued; повідомлення спостерігалося в Ready, predictions ще не існували.
3. Запущений worker виконав справжню фотомодель, опублікував результат, центральний consumer зберіг **один аналіз та рівно три predictions**.
4. Повтор початкового eventId пройшов через справжню requests queue; другого SQL-аналізу та додаткових TOP-3 не з’явилося.
5. Контракт, спільний для React/Expo, повернув UUID/statusUrl/historyId, деталі та точні байти медіа за SHA-256.
6. Пошкоджений PNG завершився Failed без predictions; завдання та некоректний JSON потрапили до DLQ.
7. Пакет із **усіх 15 початкових фотографій** завершився: **15 Completed, рівно 45 predictions** у SQL.
8. Зупинений RabbitMQ дав health 503/degraded. Новий upload отримав 202/Pending та зберігся в SQL Outbox без PublishedAt.
9. Після запуску RabbitMQ збережене Outbox-завдання автоматично було доставлено й завершилося.
10. Worker отримав **SIGKILL під час Processing** аудіозапису. Після запуску реальна аудіомодель завершила роботу, SQL зберіг один результат із TOP-3.
11. SQL-контейнер справді був зупинений, health повертав `database=false`; worker запущено з `--no-deps`. Подія результату спостерігалася в durable results retry queue.
12. Після відновлення SQL відкладений результат транзакційно збережено, predictions — рівно три.
13. Перезапущені central і worker зберегли результат, ledger та відновили consumers.
14. Історія, статистика confidence та кількість рядків CSV збіглися; Pending/Failed не додавали фіктивних confidence.

Додатково `verification/rabbitmq-replay.json` підтверджує повернення **4 подій результатів** із DLQ через Publisher Confirms, збереження **2 діагностичних повідомлень** у DLQ та відсутність дублікатів у відновлених SQL-результатах.

Початкові невдалі SQL outage-прогони не зараховано. Діагностика виявила два окремі питання: запуск worker через Compose міг відновлювати залежності; потім у справжньому SQL outage з’ясувалося, що Python передає малий `x-retry` як інший цілий AMQP-тип. Consumer виправлено для sbyte/byte/short/int/long, додано сім тестів. Збережені результати відновлено з DLQ, фінальний SQL outage-прогін успішний.

## Реальний браузер

Це перевірка справжнього React UI, не дві HTTP-сесії, що його імітують. `verification/rabbitmq-browser.json` містить ID перевірених завдань.

- Фото було вибрано через file chooser і надіслано кнопкою React при зупиненому worker. Відображалося **«Очікування в черзі»**.
- Після reload залишився **той самий UUID** і той самий стан. Файл повторно не надсилався.
- Після запуску worker з’явилися **«Аналіз завершено»**, справжні TOP-3, confidence та картка виду.
- Для WAV через React спостерігалося **«Обробка»**, потім Completed і буквальний результат `Rosy_starling`. Назва файлу `robin.wav` не виправляла результат моделі вручну.
- Виконано вхід у локальний Management UI з `.env` без виведення пароля. На Queues видно дев’ять quorum queues, Ready/Unacked та DLQ; Overview показував два активні consumers і графіки rates.

Знімки:

- [Черга до запуску worker](../verification/rabbitmq-screenshots/web-queued.jpg).
- [Завершене фото після reload](../verification/rabbitmq-screenshots/web-completed.jpg).
- [Обробка аудіо](../verification/rabbitmq-screenshots/web-processing.jpg).
- [Справжній аудіорезультат](../verification/rabbitmq-screenshots/web-audio-completed.jpg).
- [RabbitMQ Queues](../verification/rabbitmq-screenshots/management-queues.jpg).

## Збереження початкових даних

Локальний SQL Express до змін містив **36 аналізів та 108 predictions**. Створено COPY_ONLY backup у `data/backups`. Після EF-міграції повністю збіглися знімки початкових колонок Analyses, Predictions та Evaluations. Доказ — `verification/rabbitmq-migration.json`. Нові async-поля старих записів заповнюються на підставі попередньої AnalysisDate; вони не є новим вимірюванням історичного часу inference.

Docker SQL мав окремий наявний volume і нуль аналізів до цих тестів; його також зарезервовано. Docker-перевірки додали власні результати у цю базу. Локальна історія SQL Express не переносилася між серверами і не замінювалася Docker-даними.

`scripts/check_delivery.py` підтвердив **37 початкових файлів з незмінними SHA-256** та відсутність коментарів у перевірених джерелах. SQLite, CSV, sample images/audio та uploads не видалялися. Стару папку `submission` не редаговано. Розмір нового комплекту визначається `verification/submission-size.json`; `.env`, кеші, volumes, ledger, backups та build output до нього не входять.

## Межі перевірки

- Фізичний iPhone/Expo Go, системні дозволи камери/мікрофона, реальний AppState background/resume та файлове відновлення на iOS не перевірялися. TypeScript, shared polling-тести й iOS export підтверджують іншу частину системи.
- Усі 10/30/60-second inference retries і вичерпання чотирьох спроб перевірені unit-тестами. У реальному SQL outage спостерігався відкладений result retry; довге утримання SQL offline до вичерпання всіх трьох затримок окремо не моделювалося.
- Миттєвий збій мережі точно між confirm та ACK/COMMIT не інжектувався на мережевому рівні; відповідний порядок підтверджень і повторне відтворення готової відповіді перевірені unit-тестами, а реальна повторна доставка — через брокер.
- Перевірено окремі перезапуски RabbitMQ/SQL/central/worker та збереження наявних volumes. Повне видалення Docker volumes і холодне розгортання без них навмисно не виконувалося.
- Один вузол RabbitMQ не перевірявся як кластер. Стрес-тести на сотнях паралельних inference не входили до цього завдання; фактичний worker обробляє по одному повідомленню.
- Початкова sandbox-спроба expo-doctor отримала npm DNS ENOTFOUND; повтор із мережевим доступом дав 21/21. iOS export перевіряє JS bundle, а не нативну інсталяцію.

Відтворення: [README](../README.md), `scripts/verify_rabbitmq.py --batch --faults`. Тести відмов короткочасно зупиняють сервіси цього Compose та відновлюють їх у finally-блоках; не запускайте їх паралельно з іншим протоколом керування цими самими контейнерами.


## Завершальний стан

`verification/rabbitmq-final.json` підтверджує додаткове справжнє async-завдання після остаточного restart RabbitMQ: HTTP 202, Completed, один SQL-аналіз, три predictions, дві Inbox-події та published Outbox. Усі п’ять довгоживучих Docker-сервісів healthy; migration job завершився з кодом 0. Робочі/retry queues порожні, два consumers активні, два діагностичні повідомлення збережені в DLQ. У SQL немає незавершених тестових завдань. Фільтровані завершальні логи — `verification/rabbitmq-final-logs.txt`.

Окремо `verification/rabbitmq-sync-compat.json` підтверджує справжній Docker FastAPI → синхронний маршрут сумісності → SQL → читання → видалення лише створеного цим тестом нового запису. Swagger перевірено на HTTP 202 для трьох async upload routes і на наявність status API.

Кінцевий комплект для здачі підготовлено у `submission-rabbitmq`, зберігаючи стару `submission`. `scripts/verify_submission.py --directory submission-rabbitmq` перевіряє manifest hashes, фактичний розмір із маніфестом та точне відновлення початкових uploads у тимчасовій папці. Протокол — `verification/rabbitmq-submission-roundtrip.json`. Архів не створюється.
