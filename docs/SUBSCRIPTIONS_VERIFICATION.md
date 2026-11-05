# Перевірки підписок — 03.11.2026

## Фактичні результати

| Перевірка | Результат | Доказ |
|---|---|---|
| Foundry | 14 passed, fuzz 256 запусків | `verification/subscriptions-foundry.json` |
| ASP.NET + справжній MS SQL | 69 passed, 0 failed, 0 skipped | `verification/subscriptions-sql.trx` |
| Python / наявний Worker / legacy | 126 passed, 3 skipped, 0 errors | `verification/subscriptions-python.xml` |
| React | 18 passed, build і typecheck пройшли | `verification/subscriptions-client-validation.json` |
| Expo Go SDK 57 | typecheck, install check, doctor 21/21, iOS export 974 модулі | `verification/subscriptions-client-validation.json` |
| Anvil + Identity + Nethereum RPC + SQL | passed | `verification/subscriptions-blockchain.json` |
| Оплата → RabbitMQ → справжні фото/аудіомоделі → SQL | passed | `verification/subscriptions-integration.json` |
| Усі серверні компоненти у Docker Compose | passed | `verification/subscriptions-docker.json` |
| Старі дані | 36 аналізів, 108 передбачень, 33 картки, 15 оцінок; 93 файли незмінні | `verification/subscriptions-preservation.json` |

SQL перевірки включають 20 паралельних FREE-запитів (рівно 5 прийнято), 12 конкурентних обробок одного платежу (один період), атомарний outbox rollback, захист Completed від запізнілого Queued після Publisher Confirm, Identity з SQL, архів без автоматичного власника, приватність результатів, nonce/signature/domain/chain/expiry/replay, відсутність прав без Confirmed, expiry, зміну тарифу та повернення ліміту один раз. FakeBlockchain та UnitAiClient у модульних перевірках позначені окремо в коді; вони не є доказом RPC або inference.

## Реальний локальний блокчейн

Платіжний контракт: `0xe7f1725e7734ce288f8367e1bb143e90bb3f0512`. MockUSDC: `0x5fbdb2315678afecb367f032d93f642f64180aa3`. Це фактичний деплой у Anvil 31337, не адреса Base Sepolia. Його стан існує лише у відповідному запущеному локальному ланцюжку; стандартний протокол завершує власний Anvil після перевірки.

- Справжні контракти розгорнуто в Anvil; міграції застосовано в ізольованій SQL-базі.
- Identity-реєстрація, Bearer-сесія та справжній SIWE personal_sign; повторний nonce відхилено.
- Реальна реорганізація Anvil забрала права; повторне канонічне включення відновило той самий період без продовження.
- PRO: mint, точний approval, справжня подія контракту, підтвердження, активація в SQL та захист від повторної обробки.
- Фоновий сервіс зберіг Expired; негайний перехід на FREE зберіг історію.
- PREMIUM: mint, точний approval, справжня подія контракту, підтвердження, активація в SQL та захист від повторної обробки.
- Справжній локальний блокчейн-протокол завершено.

Платіжні transactionHash, blockNumber і logIndex записано з реальних receipt. `mock_used=false` у blockchain-only звіті означає справжній локальний блокчейн; `aiTestRequested=false` і `completeAiBlockchainScenario=false` явно відрізняють його від inference.

Після reorg звіт окремо зберігає початковий скасований хеш і канонічний хеш відновленої оплати. У фінальному Docker-прогоні перевірено точну рівність канонічних transactionHash і logIndex між API та SQL. Для попередніх хостових звітів записані хеші додатково звірено зі збереженими Confirmed-платежами їхніх ізольованих SQL-баз; факт цього аудиту вказано в JSON окремо від початкового RPC-прогону.

## Повний AI-протокол

Пройшов справжній сценарій RabbitMQ + Python Worker + Hugging Face після блокчейн-оплати.

Окремо пройшов той самий платіжний та AI-сценарій у Docker Compose: Anvil, ASP.NET, SQL Server, RabbitMQ, FastAPI та Worker працювали в контейнерах поточних збірок.

Повний хостовий прогін: `2026-11-03T19:07:10.243036+00:00` (UTC), база `BirdLabSubscriptionIntegration_20261103_190710`. Docker-прогін: `2026-11-03T19:28:54.283258+00:00` (UTC), окрема база `BirdLabSubscriptionIntegration_20261103_192854`. В обох успішних сценаріях PRO оплачено справжнім локальним ERC-20, receipt перевірено сервером, фото й аудіо отримали по три передбачення, а ліміт змінився 100 → 99 → 98. Моделі: `PwNzDust/vit_cub` та `greenarcade/wav2vec2-vd-bird-sound-classification`.

Docker-протокол додатково перевіряє неавторизований доступ, чужі status/history/media, заборонені FREE-функції та 20 конкурентних HTTP-запитів іншого FREE-користувача: рівно 5 прийнято й завершено реальним Worker, 15 відхилено з 429. Видалення власного тестового результату не повертає добовий ліміт; logout відкликає сесію. Зіставлено реальні SQL Outbox/Inbox, TOP-3, UsageRecords та blockchain event identity. Ці твердження про Docker підтверджуються лише коли окремий звіт має `outcome=passed` і `completeAiBlockchainScenario=true`.

Для Docker використано окремий Compose project та його власні SQL/media/RabbitMQ/worker volumes. Наявний `birds_model-cache` підключено тільки для читання з `BIRD_OFFLINE=true`. Стандартне завершення прибирає лише тестові контейнери та мережу командою `down` без `-v`; дані тестового SQL і робочі volumes збережено. Вихідний стек `birds` не перезапускався під час цього ізольованого прогону.

Перші спроби Docker виявили гонку початкової ініціалізації RabbitMQ: root-CLI міг створити `/var/lib/rabbitmq/.erlang.cookie` одночасно із запуском сервера, після чого сервер користувача `rabbitmq` отримував `eacces`. У `rabbitmq/bootstrap.sh` додано штатне виправлення власника volume та перехід у `rabbitmq` через `gosu` перед запуском сервера й CLI. Повторний прогін створює новий volume і перевіряє його старт, власника cookie та режим 400/600 без читання значення cookie. Попередні неуспішні протоколи й логи збережено локально в `.test-artifacts/subscriptions`.

## Межі доказів

Base Sepolia деплой/платіж, реальна MetaMask extension-покупка, фізичний iPhone та review магазинів не виконані. iOS JS export не є перевіркою камери, мікрофона, SecureStore чи локальної мережі на пристрої. Контракт і платіжна система не проходили незалежного аудиту.

У SDK 57 toolchain після сумісних npm-виправлень залишилися 14 advisories: 2 high, 10 moderate, 2 low; автоматичний force-перехід на Expo 58 не виконували. Web npm audit після оновлення Vitest — 0. Потрібне окреме контрольоване оновлення Expo та перевірка фізичного Expo Go.

Під час перевірок виправлено спосіб запуску тестових процесів: прямий запуск ASP.NET DLL, перевірка власного listening marker, коректне завершення власних процесів. Помилка системної pytest temp-папки усунута перенесенням basetemp у `.test-artifacts`. DLL, заблоковану Application Control після збірки в sandbox, повторно зібрано у дозволеному середовищі; захист Windows не вимикали. Скрипт тестів відмовляється вважати нуль виконаних тестів успіхом.

Керівництво, політики TTL/зміни ціни/поновлення/reorg та залишкові обмеження: [SUBSCRIPTIONS.md](SUBSCRIPTIONS.md). Повна структура й перелік змін: [SUBSCRIPTIONS_FILES.md](SUBSCRIPTIONS_FILES.md).
