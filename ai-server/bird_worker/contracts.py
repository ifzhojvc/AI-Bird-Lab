import json
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schemaVersion: Literal[1]
    eventId: UUID
    analysisId: UUID
    analysisType: Literal["image", "audio"]
    fileId: UUID
    fileSha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    createdAt: AwareDatetime
    correlationId: UUID

    @field_validator("eventId", "analysisId", "fileId", "correlationId")
    @classmethod
    def nonzero(cls, value):
        if value.int == 0:
            raise ValueError("Порожній UUID заборонено.")
        return value

    @classmethod
    def read(cls, body: bytes):
        if len(body) > 65536:
            raise ValueError("Повідомлення перевищує 64 КБ.")
        return cls.model_validate_json(body)


def encode(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")


def event(request: AnalysisRequest, status: str, attempt: int, **fields) -> dict:
    return {
        "schemaVersion": 1,
        "eventId": str(uuid4()),
        "analysisId": str(request.analysisId),
        "correlationId": str(request.correlationId),
        "causationId": str(request.eventId),
        "status": status,
        "occurredAt": datetime.now(timezone.utc).isoformat(),
        "retryCount": max(0, min(3, attempt - 1)),
        **fields,
    }
