import json
import urllib.request
from pathlib import Path


def get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=40) as response:
        return json.load(response)


def main() -> None:
    root = Path(__file__).resolve().parents[1] / "verification" / "sources"
    candidates = get("https://huggingface.co/api/models?search=cub&filter=image-classification&limit=40")
    ids = [item["id"] for item in candidates] + ["chriamue/bird-species-classifier", "dima806/bird_species_image_detection"]
    print("Candidates", ids, flush=True)
    for model in ids:
        try:
            config = get(f"https://huggingface.co/{model}/resolve/main/config.json")
            labels = config.get("id2label", {})
            print(model, config.get("architectures"), len(labels), list(labels.items())[:4], flush=True)
            if len(labels) == 200 and not str(labels.get("0", "LABEL")).startswith("LABEL"):
                metadata = get(f"https://huggingface.co/api/models/{model}")
                (root / "selected_image_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
                (root / "selected_image_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
                print("SELECTED", model, metadata["sha"], flush=True)
                return
        except Exception as exc:
            print(model, type(exc).__name__, str(exc), flush=True)


if __name__ == "__main__":
    main()
