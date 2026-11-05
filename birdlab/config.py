import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("BIRD_LAB_DATA_DIR", str(ROOT))).resolve()
DB_PATH = DATA_DIR / "birds.db"
UPLOAD_DIR = DATA_DIR / "uploads"
CSV_PATH = DATA_DIR / "bird_analysis.csv"
CATALOG_PATH = ROOT / "data" / "birds.json"
SAMPLE_DIR = ROOT / "sample_images"
MANIFEST_PATH = ROOT / "sample_manifest.csv"
MODEL_CACHE = Path(os.environ.get("BIRD_MODEL_CACHE", str(ROOT / ".cache" / "huggingface")))
IMAGE_MODEL = "PwNzDust/vit_cub"
IMAGE_REVISION = "fe8e5064afeb9ed34bd6539f992b4f8cd85af919"
AUDIO_MODEL = "greenarcade/wav2vec2-vd-bird-sound-classification"
AUDIO_REVISION = "ccc18a635d5c561ff8de26873c1db0e7c6cbc51c"
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_AUDIO_BYTES = 50 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
MAX_AUDIO_SECONDS = 60
AUDIO_SEGMENT_SECONDS = 5
UNKNOWN = "Немає даних"
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "120")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
