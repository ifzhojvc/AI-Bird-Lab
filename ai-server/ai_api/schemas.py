from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PredictionResponse(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    species_name: str = Field(min_length=1)
    scientific_name: str | None
    confidence: float = Field(ge=0, le=1)
    rank: int = Field(ge=1, le=3)


class AnalysisResponse(BaseModel):
    analysis_type: Literal["image", "audio"]
    model_id: str
    model_revision: str
    elapsed_seconds: float
    predictions: list[PredictionResponse] = Field(min_length=3, max_length=3)
    metadata: dict[str, Any]


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str


class HealthResponse(BaseModel):
    status: str
    offline: bool
    device: str
    models_cached: list[str]
