import hashlib
import os
import sqlite3
from pathlib import Path

from birdlab.config import MAX_AUDIO_BYTES, MAX_IMAGE_BYTES
from birdlab.errors import InputError


class Ledger:
    def __init__(self, folder: Path):
        folder.mkdir(parents=True, exist_ok=True)
        self.lock = (folder / "worker.lock").open("a+b")
        if os.name == "nt":
            import msvcrt

            self.lock.seek(0)
            self.lock.write(b"0")
            self.lock.flush()
            self.lock.seek(0)
            msvcrt.locking(self.lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.db = sqlite3.connect(folder / "jobs.sqlite3")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("CREATE TABLE IF NOT EXISTS jobs (analysis_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, final_body BLOB)")
        self.db.commit()

    def get(self, request):
        key = str(request.analysisId)
        fingerprint = hashlib.sha256(request.model_dump_json().encode()).hexdigest()
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO jobs(analysis_id,fingerprint) VALUES(?,?)", (key, fingerprint))
        row = self.db.execute("SELECT fingerprint,attempts,final_body FROM jobs WHERE analysis_id=?", (key,)).fetchone()
        if row[0] != fingerprint:
            raise ValueError("analysisId повторено з іншим завданням.")
        return row[1], row[2]

    def begin_attempt(self, request):
        with self.db:
            self.db.execute("UPDATE jobs SET attempts=attempts+1 WHERE analysis_id=? AND final_body IS NULL", (str(request.analysisId),))
        return self.get(request)[0]

    def finish(self, request, body: bytes):
        with self.db:
            self.db.execute("UPDATE jobs SET final_body=COALESCE(final_body,?) WHERE analysis_id=?", (body, str(request.analysisId)))
        return self.get(request)[1]

    def close(self):
        self.db.close()
        self.lock.close()


def read_media(root: Path, request) -> tuple[bytes, str]:
    root = root.resolve(strict=True)
    extensions = (".jpg", ".jpeg", ".png") if request.analysisType == "image" else (".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg")
    candidates = [root / f"{request.fileId.hex}{ext}" for ext in extensions]
    found = [p for p in candidates if p.is_file()]
    if len(found) != 1:
        raise InputError("Файл відсутній або ідентифікатор неоднозначний.")
    path = found[0]
    if path.is_symlink() or path.resolve().parent != root:
        raise InputError("Посилання за межі сховища заборонено.")
    maximum = MAX_IMAGE_BYTES if request.analysisType == "image" else MAX_AUDIO_BYTES
    with path.open("rb") as stream:
        content = stream.read(maximum + 1)
    if not content or len(content) > maximum:
        raise InputError("Некоректний розмір файлу.")
    if hashlib.sha256(content).hexdigest() != request.fileSha256:
        raise InputError("Контрольна сума файлу не збігається.")
    return content, path.name
