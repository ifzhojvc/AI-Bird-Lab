import json
import struct
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "verification" / "sources"
MODELS = {
    "image": "HaotianZG/vit-cub-200-2011-bird",
    "audio": "greenarcade/wav2vec2-vd-bird-sound-classification",
}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "AIBirdLab/1.0 educational research"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for kind, model in MODELS.items():
        metadata = json.loads(fetch(f"https://huggingface.co/api/models/{model}"))
        (OUT / f"{kind}_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        print(kind, "revision", metadata["sha"], "files", [item["rfilename"] for item in metadata["siblings"]], flush=True)
        for name in ("config.json", "preprocessor_config.json", "README.md"):
            try:
                content = fetch(f"https://huggingface.co/{model}/resolve/{metadata['sha']}/{name}")
                (OUT / f"{kind}_{name}").write_bytes(content)
                if name.endswith(".json"):
                    config = json.loads(content)
                    labels = config.get("id2label", {})
                    print(kind, name, {k: v for k, v in config.items() if k in ("architectures", "sampling_rate", "num_labels", "model_type")}, "label count", len(labels), "labels", list(labels.items())[:25], flush=True)
            except Exception as exc:
                print(kind, name, type(exc).__name__, str(exc), flush=True)
        url = f"https://huggingface.co/{model}/resolve/{metadata['sha']}/model.safetensors"
        request = urllib.request.Request(url, headers={"Range": "bytes=0-300000", "User-Agent": "AIBirdLab/1.0"})
        with urllib.request.urlopen(request, timeout=90) as response:
            size = struct.unpack("<Q", response.read(8))[0]
            header = json.loads(response.read(size))
        shapes = {k: v.get("shape") for k, v in header.items() if any(part in k for part in ("classifier", "projector"))}
        (OUT / f"{kind}_tensor_shapes.json").write_text(json.dumps(shapes, indent=2), encoding="utf-8")
        print(kind, "classifier shapes", shapes, flush=True)
    try:
        url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({"action": "query", "titles": "Northern cardinal", "prop": "pageimages|pageprops", "piprop": "original", "format": "json"})
        content = fetch(url)
        (OUT / "wikimedia_probe.json").write_bytes(content)
        print("Wikimedia", content[:1000].decode(), flush=True)
    except Exception as exc:
        print("Wikimedia", type(exc).__name__, str(exc), flush=True)


if __name__ == "__main__":
    main()
