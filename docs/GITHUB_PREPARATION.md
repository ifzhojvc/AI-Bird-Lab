# Підготовка AI Bird Lab до GitHub

Git зберігає вихідний код, EF migrations, тести, lock-файли, конфігураційні шаблони та публічні тестові зразки з джерелами й ліцензіями. Поточний набір перелічено в [GIT_COMMIT_FILES.md](GIT_COMMIT_FILES.md).

## Локальні дані

`.gitignore` виключає `.env`, приватні ключі й сховища гаманців, SQLite/MS SQL-файли та резервні копії, CSV історії, uploads, `central-server/storage`, приватні `data/`, Docker volumes, Hugging Face, venv/node_modules, кеші, збірки, Expo, Foundry out/cache/broadcast, submission та локальну `verification/`. `.env.example` залишається публічним із порожніми секретними значеннями. `data/birds.json` є публічним вихідним довідником; `data/field_notes.json` зберігається локально.

Ігнорування не стирає файли з комп'ютера. Якщо секрет уже потрапив у старий коміт, зміна `.gitignore` не прибирає його з історії: потрібні окреме відкликання секрету та узгоджене очищення історії. Не використовуйте Git як резервну копію робочої бази.

## Перевірка перед комітом

Потрібен локальний [Gitleaks](https://github.com/gitleaks/gitleaks/releases). Скрипт знаходить його в PATH або `.tools/gitleaks-8.30.1/gitleaks.exe`; інший шлях передайте через `--gitleaks`.

```powershell
.\.venv\Scripts\python.exe scripts/check_git_ready.py
git add -- .
.\.venv\Scripts\python.exe scripts/check_git_ready.py --staged
git diff --cached --stat
git diff --cached --check
git status --short --branch
```

Перевірка читає фактичні blobs індексу в режимі `--staged`, шукає секрети Gitleaks із повним редагуванням значень, додатково звіряє локальні секрети з `.env`, перевіряє private key/seed phrase матеріал, порожні секретні поля `.env.example`, обов'язкові вихідні файли та правила ігнорування. Звіти з іменами файлів і номерами рядків створюються тільки в ігнорованій `.test-artifacts/git-preparation/`; значення секретів не друкуються. Евристичні перевірки допомагають виявляти секрети, але не доводять відсутність будь-яких можливих секретів.

Конфігурація `.gitleaks.toml` розширює стандартні правила. Вузький виняток стосується лише точного публічного [контракту USDC Circle у Base Sepolia](https://developers.circle.com/stablecoins/usdc-contract-addresses) у трьох конфігураційних/документаційних файлах. Каталоги тестів і документації повністю не виключаються зі сканування.

GitHub блокує звичайні Git-файли понад 100 MiB та попереджає про файли понад 50 MiB. Порогові значення перевіряє скрипт; великі моделі та робочі бази залишаються локальними. [Офіційні обмеження GitHub](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).

## Публікація

Підготовка не створює коміт, remote або GitHub-репозиторій. Перший commit і push виконуйте лише після перевірки списку файлів та явного погодження власника. URL remote має бути SSH або HTTPS без вбудованого токена; адресу й видимість GitHub-репозиторію обирає власник. Не додавайте токени, seed phrases або приватні ключі в команди, документацію чи повідомлення коміту.
