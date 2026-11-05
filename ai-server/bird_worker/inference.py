from pathlib import Path

from ai_api.audio import decode_audio
from birdlab.files import load_image
from birdlab.models import classify_audio, classify_image
from bird_worker.storage import read_media


def infer(request, root: Path, offline: bool):
    content, name = read_media(root, request)
    if request.analysisType == "image":
        result = classify_image(load_image(content, name), offline)
    else:
        result = classify_audio(decode_audio(content, name), offline)
    return {
        "predictedSpecies": result.predictions[0].label,
        "confidence": result.predictions[0].score,
        "predictions": [{"species": p.label, "scientificName": p.scientific_name, "confidence": p.score, "rank": i} for i, p in enumerate(result.predictions, 1)],
        "modelName": result.model_id,
        "modelRevision": result.revision,
        "elapsedSeconds": result.elapsed_seconds,
        "metadata": {**result.metadata, "mock_used": False},
    }
