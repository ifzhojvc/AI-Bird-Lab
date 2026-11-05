import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from birdlab.domain import InferenceResult, validate_predictions
from birdlab.errors import StorageError


SCHEMA = """
CREATE TABLE IF NOT EXISTS bird_info (
    scientific_name TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_type TEXT NOT NULL CHECK(analysis_type IN ('image','audio')),
    original_name TEXT NOT NULL,
    file_path TEXT NOT NULL UNIQUE,
    file_hash TEXT NOT NULL,
    predicted_species TEXT NOT NULL,
    scientific_name TEXT,
    confidence REAL NOT NULL CHECK(confidence BETWEEN 0 AND 1),
    model_name TEXT NOT NULL,
    model_id TEXT NOT NULL,
    model_revision TEXT NOT NULL,
    analysis_date TEXT NOT NULL,
    elapsed_seconds REAL NOT NULL,
    description TEXT NOT NULL,
    bird_snapshot TEXT NOT NULL,
    metadata TEXT NOT NULL,
    FOREIGN KEY(scientific_name) REFERENCES bird_info(scientific_name)
);
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    rank INTEGER NOT NULL CHECK(rank BETWEEN 1 AND 3),
    label TEXT NOT NULL,
    scientific_name TEXT,
    score REAL NOT NULL CHECK(score BETWEEN 0 AND 1),
    UNIQUE(analysis_id, rank)
);
CREATE TABLE IF NOT EXISTS evaluations (
    analysis_id INTEGER PRIMARY KEY REFERENCES analyses(id) ON DELETE CASCADE,
    expected_label TEXT NOT NULL,
    expected_scientific TEXT NOT NULL,
    label_source TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    top1_correct INTEGER NOT NULL CHECK(top1_correct IN (0,1)),
    top3_correct INTEGER NOT NULL CHECK(top3_correct IN (0,1)),
    experiment TEXT NOT NULL DEFAULT 'original'
);
CREATE INDEX IF NOT EXISTS idx_analysis_date ON analyses(analysis_date);
CREATE INDEX IF NOT EXISTS idx_analysis_type ON analyses(analysis_type);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Repository:
    def __init__(self, db_path: Path, upload_dir: Path):
        self.db_path = Path(db_path)
        self.upload_dir = Path(upload_dir).resolve()
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            with self.connection() as connection:
                connection.executescript(SCHEMA)
        except OSError as exc:
            raise StorageError("Не вдалося створити папку даних. Перевірте права доступу.") from exc

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = None
        try:
            connection = sqlite3.connect(self.db_path, timeout=15)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA journal_mode = WAL")
            with connection:
                yield connection
        except sqlite3.Error as exc:
            raise StorageError("Помилка бази даних. Перевірте доступ до birds.db та вільне місце.") from exc
        finally:
            if connection is not None:
                connection.close()

    def media_path(self, record: dict) -> Path:
        path = (self.upload_dir.parent / record["file_path"]).resolve()
        if not path.is_relative_to(self.upload_dir) or path == self.upload_dir:
            raise StorageError("Шлях файлу виходить за межі папки завантажень. Операцію скасовано.")
        return path

    def save(self, kind: str, original_name: str, path: Path, file_hash: str, result: InferenceResult, bird: dict | None = None, evaluation: dict | None = None) -> int:
        validate_predictions([p.to_dict() for p in result.predictions])
        if kind not in ("image", "audio"):
            raise StorageError("Невідомий тип аналізу.")
        path = path.resolve()
        if not path.is_relative_to(self.upload_dir) or not path.is_file():
            raise StorageError("Збережений файл не знайдено в папці завантажень.")
        bird = bird or {}
        top = result.predictions[0]
        scientific = top.scientific_name if top.scientific_name == bird.get("scientific_name") else None
        description = "Найвище модельне значення confidence; присутність виду не підтверджена незалежно."
        if kind == "audio" and top.label == "background":
            description = "Найвищий результат — фоновий звук. Пташиний вид не визначено."
        timestamp = now_iso()
        with self.connection() as connection:
            if scientific:
                connection.execute("INSERT INTO bird_info VALUES (?, ?, ?) ON CONFLICT(scientific_name) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at", (scientific, json.dumps(bird, ensure_ascii=False), timestamp))
            cursor = connection.execute("INSERT INTO analyses (analysis_type, original_name, file_path, file_hash, predicted_species, scientific_name, confidence, model_name, model_id, model_revision, analysis_date, elapsed_seconds, description, bird_snapshot, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (kind, Path(original_name.replace("\\", "/")).name, path.relative_to(self.upload_dir.parent).as_posix(), file_hash, top.label, scientific, top.score, "ViT CUB-200" if kind == "image" else "Wav2Vec2 Vedanthangal", result.model_id, result.revision, timestamp, result.elapsed_seconds, description, json.dumps(bird, ensure_ascii=False), json.dumps(result.metadata, ensure_ascii=False)))
            analysis_id = int(cursor.lastrowid)
            connection.executemany("INSERT INTO predictions (analysis_id, rank, label, scientific_name, score) VALUES (?, ?, ?, ?, ?)", [(analysis_id, rank, p.label, p.scientific_name, p.score) for rank, p in enumerate(result.predictions, 1)])
            if evaluation:
                if kind != "image" or not evaluation.get("label_source") or evaluation.get("file_hash") != file_hash:
                    raise StorageError("Немає підтвердженої еталонної мітки для оцінювання.")
                expected = evaluation["expected_label"]
                labels = [p.label for p in result.predictions]
                connection.execute("INSERT INTO evaluations VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (analysis_id, expected, evaluation["expected_scientific"], evaluation["label_source"], file_hash, int(labels[0] == expected), int(expected in labels), evaluation.get("experiment", "original")))
        return analysis_id

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict:
        data = dict(row)
        data["bird"] = json.loads(data.pop("bird_snapshot"))
        data["metadata"] = json.loads(data["metadata"])
        return data

    def all(self, search: str = "", kind: str | None = None, descending: bool = True) -> list[dict]:
        query = "SELECT * FROM analyses"
        params = []
        if kind in ("image", "audio"):
            query += " WHERE analysis_type = ?"
            params.append(kind)
        query += " ORDER BY analysis_date " + ("DESC, id DESC" if descending else "ASC, id ASC")
        with self.connection() as connection:
            records = [self._decode(row) for row in connection.execute(query, params).fetchall()]
        needle = search.strip().casefold()
        if needle:
            records = [r for r in records if needle in " ".join(str(value or "") for value in (r["predicted_species"], r["scientific_name"], r["bird"].get("ukrainian_name"), r["bird"].get("english_name"))).casefold()]
        return records

    def get(self, analysis_id: int) -> dict | None:
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
            if row is None:
                return None
            record = self._decode(row)
            record["predictions"] = [dict(p) for p in connection.execute("SELECT rank, label, scientific_name, score FROM predictions WHERE analysis_id = ? ORDER BY rank", (analysis_id,)).fetchall()]
            evaluation = connection.execute("SELECT * FROM evaluations WHERE analysis_id = ?", (analysis_id,)).fetchone()
            record["evaluation"] = dict(evaluation) if evaluation else None
            return record

    def evaluations(self) -> list[dict]:
        with self.connection() as connection:
            return [dict(row) for row in connection.execute("SELECT e.*, a.model_id, a.model_revision, a.original_name FROM evaluations e JOIN analyses a ON a.id=e.analysis_id ORDER BY e.analysis_id").fetchall()]

    def delete_many(self, ids: list[int]) -> int:
        moved = []
        deleted = 0
        try:
            with self.connection() as connection:
                for analysis_id in ids:
                    row = connection.execute("SELECT file_path FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
                    if row is None:
                        continue
                    path = self.media_path(dict(row))
                    if path.exists():
                        quarantine = self.upload_dir / f"{uuid.uuid4().hex}.tmp"
                        path.rename(quarantine)
                        moved.append((path, quarantine))
                    connection.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
                    deleted += 1
        except (OSError, StorageError) as exc:
            for original, quarantine in reversed(moved):
                if quarantine.exists():
                    quarantine.rename(original)
            if isinstance(exc, StorageError):
                raise
            raise StorageError("Не вдалося видалити файл. Перевірте, чи не відкрито його іншою програмою.") from exc
        for _, quarantine in moved:
            try:
                quarantine.unlink(missing_ok=True)
            except OSError as exc:
                raise StorageError("Запис видалено, але тимчасовий файл .tmp у uploads ще зайнятий іншою програмою.") from exc
        return deleted

    def delete(self, analysis_id: int) -> bool:
        return self.delete_many([analysis_id]) > 0

    def clear(self) -> int:
        return self.delete_many([row["id"] for row in self.all()])
