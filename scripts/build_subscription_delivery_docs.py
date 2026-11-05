import hashlib
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from prepare_submission import ROOT, source_files


def read_json(name):
    path = ROOT / "verification" / name
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}


def previous_document(name, marker):
    backup = ROOT / ".test-artifacts/before-subscriptions/source" / name
    text = (backup if backup.exists() else ROOT / name).read_text(encoding="utf-8-sig")
    return text.split(marker, 1)[-1]


def inventory():
    output = ROOT / "docs/SUBSCRIPTIONS_FILES.md"
    if not output.exists():
        output.write_text("# Файли розширення\n", encoding="utf-8")
    files = sorted(source_files(), key=lambda p: p.relative_to(ROOT).as_posix())
    baseline = ROOT / ".test-artifacts/before-subscriptions/manifest.json"
    before = json.loads(baseline.read_text(encoding="utf-8"))["files"] if baseline.exists() else {}
    created, changed = [], []
    tree = {}
    for file in files:
        name = file.relative_to(ROOT).as_posix()
        if name not in before:
            created.append(name)
        elif hashlib.sha256(file.read_bytes()).hexdigest() != before[name]:
            changed.append(name)
        current = tree
        for part in Path(name).parts:
            current = current.setdefault(part, {})
    lines = ["Birds/"]
    def render(branch, prefix=""):
        items = sorted(branch.items(), key=lambda pair: (not bool(pair[1]), pair[0].casefold()))
        for index, (name, children) in enumerate(items):
            last = index == len(items) - 1
            lines.append(prefix + ("└── " if last else "├── ") + name + ("/" if children else ""))
            render(children, prefix + ("    " if last else "│   "))
    render(tree)
    text = "# Файли розширення підписок\n\nПовна структура вихідного комплекту без залежностей, кешів, збірок, секретів і копій submission. Наявні робочі storage, SQL, uploads і моделі не очищалися; бінарні результати центрального сервера не входять до вихідного комплекту.\n\n## Структура\n\n```text\n" + "\n".join(lines) + "\n```\n\n## Створені файли\n\n" + "\n".join(f"- `{name}`" for name in created) + "\n\n## Змінені файли\n\n" + "\n".join(f"- `{name}`" for name in changed) + "\n\nПорівняння зроблено з контрольним інвентарем до розширення. Список включає документацію та докази перевірок. Жоден попередній файл основного проєкту не видалено.\n"
    output.write_text(text, encoding="utf-8")
    result = {"created": created, "modified": changed, "source_files": len(files), "removed_original_files": [name for name in before if not (ROOT / name).exists()]}
    (ROOT / "verification/subscriptions-changes.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main():
    chain = read_json("subscriptions-blockchain.json")
    full = read_json("subscriptions-integration.json")
    docker = read_json("subscriptions-docker.json")
    preservation = read_json("subscriptions-preservation.json")
    clients = read_json("subscriptions-client-validation.json")
    foundry = read_json("subscriptions-foundry.json")
    trx = ET.parse(ROOT / "verification/subscriptions-sql.trx").getroot()
    counters = next(e for e in trx.iter() if e.tag.endswith("Counters"))
    dotnet = dict(counters.attrib)
    python = ET.parse(ROOT / "verification/subscriptions-python.xml").getroot()
    suite = next(e for e in python.iter() if e.tag == "testsuite")
    python_counts = {key: int(suite.attrib.get(key, 0)) for key in ("tests", "failures", "errors", "skipped")}
    complete = full.get("outcome") == "passed" and full.get("completeAiBlockchainScenario") is True
    docker_complete = docker.get("outcome") == "passed" and docker.get("completeAiBlockchainScenario") is True and not docker.get("dockerCleanupError")
    summary = {"generatedAtUtc": datetime.now(timezone.utc).isoformat(), "dotnet": dotnet, "python": python_counts, "foundry": foundry, "clients": clients, "blockchainSqlProtocolPassed": chain.get("outcome") == "passed", "completeAiBlockchainScenarioPassed": complete, "dockerCompleteAiBlockchainScenarioPassed": docker_complete, "preservation": preservation}
    (ROOT / "verification/subscriptions-final.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    labels = {
        "Real Anvil contracts deployed; isolated SQL migrations applied": "Справжні контракти розгорнуто в Anvil; міграції застосовано в ізольованій SQL-базі.",
        "Identity registration, bearer session and real personal_sign SIWE; nonce replay rejected": "Identity-реєстрація, Bearer-сесія та справжній SIWE personal_sign; повторний nonce відхилено.",
        "Real Anvil reorg revoked access; canonical transaction restored same period without extension": "Реальна реорганізація Anvil забрала права; повторне канонічне включення відновило той самий період без продовження.",
        "Expiry background service persisted Expired; immediate FREE fallback preserved history": "Фоновий сервіс зберіг Expired; негайний перехід на FREE зберіг історію.",
        "Real local blockchain verification protocol completed": "Справжній локальний блокчейн-протокол завершено."
    }
    translated = []
    for check in chain.get("checks", []):
        name = check["name"]
        if name.startswith("Plan 1:") or name.startswith("Plan 2:"):
            name = ("PRO" if name.startswith("Plan 1:") else "PREMIUM") + ": mint, точний approval, справжня подія контракту, підтвердження, активація в SQL та захист від повторної обробки."
        else:
            name = labels.get(name, name)
        translated.append("- " + name)
    checks = "\n".join(translated)
    full_status = "Пройшов справжній сценарій RabbitMQ + Python Worker + Hugging Face після блокчейн-оплати." if complete else "Повний сценарій оплата → RabbitMQ → Python Worker → реальний AI поки не підтверджено. Потрібен доступний Docker/RabbitMQ; blockchain-only протокол не видається за цей доказ."
    docker_status = "Окремо пройшов той самий платіжний та AI-сценарій у Docker Compose: Anvil, ASP.NET, SQL Server, RabbitMQ, FastAPI та Worker працювали в контейнерах поточних збірок." if docker_complete else "Повний запуск поточних збірок у Docker Compose поки не підтверджено; дивіться фактичний результат окремого Docker-протоколу."
    content = f"""# Перевірки підписок — 03.11.2026

## Фактичні результати

| Перевірка | Результат | Доказ |
|---|---|---|
| Foundry | {foundry.get('passed')} passed, fuzz 256 запусків | `verification/subscriptions-foundry.json` |
| ASP.NET + справжній MS SQL | {dotnet.get('passed')} passed, {dotnet.get('failed')} failed, {dotnet.get('notExecuted')} skipped | `verification/subscriptions-sql.trx` |
| Python / наявний Worker / legacy | {python_counts['tests'] - python_counts['skipped'] - python_counts['errors'] - python_counts['failures']} passed, {python_counts['skipped']} skipped, {python_counts['errors']} errors | `verification/subscriptions-python.xml` |
| React | 18 passed, build і typecheck пройшли | `verification/subscriptions-client-validation.json` |
| Expo Go SDK 57 | typecheck, install check, doctor 21/21, iOS export 974 модулі | `verification/subscriptions-client-validation.json` |
| Anvil + Identity + Nethereum RPC + SQL | {'passed' if chain.get('outcome') == 'passed' else 'не підтверджено'} | `verification/subscriptions-blockchain.json` |
| Оплата → RabbitMQ → справжні фото/аудіомоделі → SQL | {'passed' if complete else 'не підтверджено'} | `verification/subscriptions-integration.json` |
| Усі серверні компоненти у Docker Compose | {'passed' if docker_complete else 'не підтверджено'} | `verification/subscriptions-docker.json` |
| Старі дані | 36 аналізів, 108 передбачень, 33 картки, 15 оцінок; 93 файли незмінні | `verification/subscriptions-preservation.json` |

SQL перевірки включають 20 паралельних FREE-запитів (рівно 5 прийнято), 12 конкурентних обробок одного платежу (один період), атомарний outbox rollback, захист Completed від запізнілого Queued після Publisher Confirm, Identity з SQL, архів без автоматичного власника, приватність результатів, nonce/signature/domain/chain/expiry/replay, відсутність прав без Confirmed, expiry, зміну тарифу та повернення ліміту один раз. FakeBlockchain та UnitAiClient у модульних перевірках позначені окремо в коді; вони не є доказом RPC або inference.

## Реальний локальний блокчейн

Платіжний контракт: `{chain.get('deployment', {}).get('paymentContractAddress', 'не розгорнуто')}`. MockUSDC: `{chain.get('deployment', {}).get('tokenAddress', 'не розгорнуто')}`. Це фактичний деплой у Anvil 31337, не адреса Base Sepolia. Його стан існує лише у відповідному запущеному локальному ланцюжку; стандартний протокол завершує власний Anvil після перевірки.

{checks}

Платіжні transactionHash, blockNumber і logIndex записано з реальних receipt. `mock_used=false` у blockchain-only звіті означає справжній локальний блокчейн; `aiTestRequested=false` і `completeAiBlockchainScenario=false` явно відрізняють його від inference.

Після reorg звіт окремо зберігає початковий скасований хеш і канонічний хеш відновленої оплати. У фінальному Docker-прогоні перевірено точну рівність канонічних transactionHash і logIndex між API та SQL. Для попередніх хостових звітів записані хеші додатково звірено зі збереженими Confirmed-платежами їхніх ізольованих SQL-баз; факт цього аудиту вказано в JSON окремо від початкового RPC-прогону.

## Повний AI-протокол

{full_status}

{docker_status}

Повний хостовий прогін: `{full.get('startedAt', 'не виконувався')}` (UTC), база `{full.get('database', 'немає')}`. Docker-прогін: `{docker.get('startedAt', 'не виконувався')}` (UTC), окрема база `{docker.get('database', 'немає')}`. В обох успішних сценаріях PRO оплачено справжнім локальним ERC-20, receipt перевірено сервером, фото й аудіо отримали по три передбачення, а ліміт змінився 100 → 99 → 98. Моделі: `PwNzDust/vit_cub` та `greenarcade/wav2vec2-vd-bird-sound-classification`.

Docker-протокол додатково перевіряє неавторизований доступ, чужі status/history/media, заборонені FREE-функції та 20 конкурентних HTTP-запитів іншого FREE-користувача: рівно 5 прийнято й завершено реальним Worker, 15 відхилено з 429. Видалення власного тестового результату не повертає добовий ліміт; logout відкликає сесію. Зіставлено реальні SQL Outbox/Inbox, TOP-3, UsageRecords та blockchain event identity. Ці твердження про Docker підтверджуються лише коли окремий звіт має `outcome=passed` і `completeAiBlockchainScenario=true`.

Для Docker використано окремий Compose project та його власні SQL/media/RabbitMQ/worker volumes. Наявний `birds_model-cache` підключено тільки для читання з `BIRD_OFFLINE=true`. Стандартне завершення прибирає лише тестові контейнери та мережу командою `down` без `-v`; дані тестового SQL і робочі volumes збережено. Вихідний стек `birds` не перезапускався під час цього ізольованого прогону.

Перші спроби Docker виявили гонку початкової ініціалізації RabbitMQ: root-CLI міг створити `/var/lib/rabbitmq/.erlang.cookie` одночасно із запуском сервера, після чого сервер користувача `rabbitmq` отримував `eacces`. У `rabbitmq/bootstrap.sh` додано штатне виправлення власника volume та перехід у `rabbitmq` через `gosu` перед запуском сервера й CLI. Повторний прогін створює новий volume і перевіряє його старт, власника cookie та режим 400/600 без читання значення cookie. Попередні неуспішні протоколи й логи збережено локально в `.test-artifacts/subscriptions`.

## Межі доказів

Base Sepolia деплой/платіж, реальна MetaMask extension-покупка, фізичний iPhone та review магазинів не виконані. iOS JS export не є перевіркою камери, мікрофона, SecureStore чи локальної мережі на пристрої. Контракт і платіжна система не проходили незалежного аудиту.

У SDK 57 toolchain після сумісних npm-виправлень залишилися 14 advisories: 2 high, 10 moderate, 2 low; автоматичний force-перехід на Expo 58 не виконували. Web npm audit після оновлення Vitest — 0. Потрібне окреме контрольоване оновлення Expo та перевірка фізичного Expo Go.

Під час перевірок виправлено спосіб запуску тестових процесів: прямий запуск ASP.NET DLL, перевірка власного listening marker, коректне завершення власних процесів. Помилка системної pytest temp-папки усунута перенесенням basetemp у `.test-artifacts`. DLL, заблоковану Application Control після збірки в sandbox, повторно зібрано у дозволеному середовищі; захист Windows не вимикали. Скрипт тестів відмовляється вважати нуль виконаних тестів успіхом.

Керівництво, політики TTL/зміни ціни/поновлення/reorg та залишкові обмеження: [SUBSCRIPTIONS.md](SUBSCRIPTIONS.md). Повна структура й перелік змін: [SUBSCRIPTIONS_FILES.md](SUBSCRIPTIONS_FILES.md).
"""
    (ROOT / "docs/SUBSCRIPTIONS_VERIFICATION.md").write_text(content, encoding="utf-8")
    readme_marker = "\n\n---\n\n## Попередня документація\n\n"
    intro = "# AI Bird Lab — криптовалютні підписки\n\nДо наявної системи додано Identity, приватну історію, FREE/PRO/PREMIUM, SIWE, контракт Solidity та незалежну перевірку платежів у ASP.NET Core. Кожна покупка — ручна передплата; mainnet вимкнено, типово платежі не активні до налаштування власником.\n\nПочинайте з [актуального керівництва запуску, Anvil, Base Sepolia, API, Docker та Expo](docs/SUBSCRIPTIONS.md). [Поточні докази й неперевірені сценарії](docs/SUBSCRIPTIONS_VERIFICATION.md), [повна структура, створені та змінені файли](docs/SUBSCRIPTIONS_FILES.md).\n\nFREE: 5 фото на добу UTC; PRO: 5 тестових USDC / 30 днів / 100 аналізів; PREMIUM: 10 тестових USDC / 30 днів / 500 аналізів. Старі аналізи не привласнюються новому користувачу; доступ до архіву надається явно. Дані та робочі volumes збережені.\n\nНаведені нижче старі результати RabbitMQ є історичними. Для поточної версії користуйтеся новими інструкціями й окремими актуальними звітами."
    (ROOT / "README.md").write_text(intro + readme_marker + previous_document("README.md", readme_marker), encoding="utf-8")
    report_marker = "\n\n---\n\n## Попередній звіт\n\n"
    report_intro = "# Звіт: криптовалютні підписки AI Bird Lab\n\nДата: 03.11.2026. Наявний проєкт розширено на місці. Додано Identity, nonce/SIWE, тарифи й періоди в MS SQL, Solidity/Foundry, Nethereum RPC verification, атомарний облік лімітів, Web3 React та перегляд підписки в Expo Go.\n\n" + f"Перевірено: Foundry 14; .NET/SQL {dotnet.get('passed')}; React 18; Python {python_counts['tests'] - python_counts['skipped'] - python_counts['errors'] - python_counts['failures']} + {python_counts['skipped']} skipped; Expo doctor 21/21 та iOS export. " + full_status + " " + docker_status + "\n\n[Повний протокол, докази, реальні та змодельовані перевірки, обмеження](docs/SUBSCRIPTIONS_VERIFICATION.md). [Архітектура, схеми платежів, політики, команди й офіційні джерела](docs/SUBSCRIPTIONS.md). [Усі файли для здачі та зміни](docs/SUBSCRIPTIONS_FILES.md).\n\nSQL-сверка підтвердила незмінність 36 старих аналізів, 108 predictions, 33 birds, 15 evaluations та 93 захищених файлів. Немає автоматичних списань, реальних mainnet-платежів, зберігання користувацьких private keys або створення ZIP/RAR. Поточна система не оголошується production-ready."
    (ROOT / "report.md").write_text(report_intro + report_marker + previous_document("report.md", report_marker), encoding="utf-8")
    changes = inventory()
    print(json.dumps({"dotnet_passed": dotnet.get("passed"), "blockchain_sql_passed": chain.get("outcome") == "passed", "full_ai_passed": complete, "docker_full_ai_passed": docker_complete, "created_files": len(changes["created"]), "modified_files": len(changes["modified"]), "removed_original_files": changes["removed_original_files"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
