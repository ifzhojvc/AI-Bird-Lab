import hashlib
import json
from pathlib import Path

import requests
import soundfile as sf


ROOT = Path(__file__).resolve().parents[1]
BASE = "https://librosa.org/data/audio/456440__inspectorj__bird-whistling-robin-single-13"


def main() -> None:
    directory = ROOT / "sample_audio"
    directory.mkdir(exist_ok=True)
    license_response = requests.get(BASE + ".txt", timeout=45)
    license_response.raise_for_status()
    text = license_response.text
    print(text, flush=True)
    if "creativecommons.org/licenses/by/" not in text and "creativecommons.org/publicdomain/zero/" not in text:
        raise RuntimeError("Відкриту ліцензію запису не підтверджено; аудіо не завантажено.")
    response = requests.get(BASE + ".ogg", timeout=90)
    response.raise_for_status()
    source = directory / "robin_original.ogg"
    source.write_bytes(response.content)
    samples, rate = sf.read(source, dtype="float32")
    sf.write(directory / "robin.wav", samples, rate, subtype="PCM_16")
    (directory / "LICENSE.txt").write_text(text, encoding="utf-8")
    metadata = {"source": "https://freesound.org/people/InspectorJ/sounds/456440/", "mirror": BASE + ".ogg", "author": "InspectorJ", "original_description": "Bird Whistling, Robin, Single, 13.wav", "license_text": text, "file_name": "robin.wav", "sha256": hashlib.sha256((directory / "robin.wav").read_bytes()).hexdigest(), "sample_rate": rate, "duration_seconds": len(samples) / rate, "processing": "Decoded OGG mirror to PCM16 WAV; no synthetic sound or relabeling", "accuracy_evaluated": False, "limitation": "The source calls the bird robin; this class is outside the audio model label set. No species accuracy is claimed."}
    (directory / "manifest.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in metadata.items() if k != "license_text"}, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
