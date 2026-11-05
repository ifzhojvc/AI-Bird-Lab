import json
import sys
import time
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from birdlab.config import AUDIO_MODEL, AUDIO_REVISION, IMAGE_MODEL, IMAGE_REVISION, MODEL_CACHE, ROOT


def main() -> None:
    from huggingface_hub import snapshot_download
    from safetensors import safe_open

    out = ROOT / "verification" / "sources"
    out.mkdir(parents=True, exist_ok=True)
    for kind, model_id, revision in (("selected_image", IMAGE_MODEL, IMAGE_REVISION), ("audio", AUDIO_MODEL, AUDIO_REVISION)):
        print(f"Завантаження {model_id} @ {revision}", flush=True)
        short_kind = "image" if kind == "selected_image" else "audio"
        for attempt in range(4):
            try:
                folder = Path(snapshot_download(model_id, revision=revision, local_dir=str(MODEL_CACHE / f"{short_kind}--{revision}"), allow_patterns=["config.json", "preprocessor_config.json", "model.safetensors", "README.md"], max_workers=2))
                break
            except Exception as exc:
                if attempt == 3:
                    raise
                print("Перервано завантаження, повторна спроба з докачуванням:", type(exc).__name__, flush=True)
                time.sleep(2 * (attempt + 1))
        config = json.loads((folder / "config.json").read_text())
        with safe_open(str(folder / "model.safetensors"), framework="pt", device="cpu") as handle:
            shapes = {name: list(handle.get_slice(name).get_shape()) for name in handle.keys() if "classifier" in name}
        for name in ("config.json", "preprocessor_config.json", "README.md"):
            if (folder / name).exists():
                (out / f"{kind}_{name}").write_bytes((folder / name).read_bytes())
        (out / f"{kind}_tensor_shapes.json").write_text(json.dumps(shapes, indent=2), encoding="utf-8")
        print("Кількість класів:", len(config["id2label"]), "Вихідний шар:", shapes, flush=True)
    from birdlab.models import get_audio_model, get_image_model

    for loader in (get_image_model, get_audio_model):
        bundle = loader(True)
        print(type(bundle.classifier.model).__name__, "пристрій", bundle.classifier.device, "частота", bundle.sample_rate, flush=True)


if __name__ == "__main__":
    main()
