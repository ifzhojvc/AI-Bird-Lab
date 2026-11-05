import asyncio
import hmac
import logging
import os
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from birdlab.config import MAX_AUDIO_BYTES, MAX_IMAGE_BYTES
from birdlab.errors import InputError, ModelError
from birdlab.files import load_image
from birdlab.models import _cached_model, classify_audio, classify_image
from ai_api.audio import decode_audio
from ai_api.schemas import AnalysisResponse, ErrorResponse, HealthResponse, PredictionResponse


logger = logging.getLogger("birdlab.ai")
logging.basicConfig(level=logging.INFO)
app = FastAPI(title="AI Bird Lab · AI Server", version="2.0.0")
inference_gate = asyncio.Semaphore(2)
OFFLINE = os.getenv("BIRD_OFFLINE", "true").lower() == "true"


class BodyLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        consumed = 0

        async def limited_receive():
            nonlocal consumed
            message = await receive()
            consumed += len(message.get("body", b""))
            if consumed > MAX_AUDIO_BYTES + 1024 * 1024:
                raise HTTPException(413, "Максимальний розмір запиту — 51 МБ.")
            return message

        await self.app(scope, limited_receive, send)


app.add_middleware(BodyLimit)


async def authorize(x_ai_key: str = Header(default="")):
    required = os.getenv("AI_INTERNAL_KEY", "")
    if required and not hmac.compare_digest(required, x_ai_key):
        raise HTTPException(401, "Невірний внутрішній ключ сервісу.")


def error(request: Request, status: int, code: str, message: str):
    request_id = str(uuid.uuid4())
    logger.warning("request=%s path=%s status=%s code=%s", request_id, request.url.path, status, code)
    return JSONResponse(status_code=status, content=ErrorResponse(code=code, message=message, request_id=request_id).model_dump())


@app.exception_handler(InputError)
async def invalid_input(request: Request, exc: InputError):
    return error(request, 422, "invalid_file", str(exc))


@app.exception_handler(ModelError)
async def unavailable_model(request: Request, exc: ModelError):
    logger.exception("Model inference failed")
    return error(request, 503, "model_unavailable", str(exc))


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return error(request, exc.status_code, "request_error", str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return error(request, 422, "validation_error", "Надішліть файл у multipart-полі file.")


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logger.exception("Unexpected AI server failure")
    return error(request, 500, "internal_error", "Внутрішня помилка AI-сервісу.")


@app.get("/health", response_model=HealthResponse, dependencies=[Depends(authorize)])
def health():
    return HealthResponse(status="ok", offline=OFFLINE, device=os.getenv("BIRD_DEVICE", "auto"), models_cached=_cached_model.loaded_kinds())


async def predict(file: UploadFile, kind: str):
    name = Path((file.filename or "").replace("\\", "/")).name
    limit = MAX_IMAGE_BYTES if kind == "image" else MAX_AUDIO_BYTES
    content = bytearray()
    try:
        while chunk := await file.read(1024 * 1024):
            content.extend(chunk)
            if len(content) > limit:
                raise HTTPException(413, f"Файл перевищує ліміт {limit // (1024 * 1024)} МБ.")
    finally:
        await file.close()
    async with inference_gate:
        if kind == "image":
            media = await run_in_threadpool(load_image, bytes(content), name)
            result = await run_in_threadpool(classify_image, media, OFFLINE)
        else:
            media = await run_in_threadpool(decode_audio, bytes(content), name)
            result = await run_in_threadpool(classify_audio, media, OFFLINE)
    logger.info("type=%s model=%s elapsed=%.3f", kind, result.model_id, result.elapsed_seconds)
    return AnalysisResponse(analysis_type=kind, model_id=result.model_id, model_revision=result.revision, elapsed_seconds=result.elapsed_seconds, predictions=[PredictionResponse(species_name=p.label, scientific_name=p.scientific_name, confidence=p.score, rank=rank) for rank, p in enumerate(result.predictions, 1)], metadata={"mock_used": False, **result.metadata})


@app.post("/predict/image", response_model=AnalysisResponse, responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}}, dependencies=[Depends(authorize)])
async def predict_image(file: UploadFile):
    return await predict(file, "image")


@app.post("/predict/audio", response_model=AnalysisResponse, responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}}, dependencies=[Depends(authorize)])
async def predict_audio(file: UploadFile):
    return await predict(file, "audio")
