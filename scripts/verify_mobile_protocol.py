import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import imageio_ffmpeg
import requests


ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:5100"


def main():
    target = ROOT / ".test-artifacts" / "mobile-recording.m4a"
    target.parent.mkdir(exist_ok=True)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-nostdin", "-y", "-v", "error", "-i", str(ROOT / "sample_audio" / "robin.wav"), "-c:a", "aac", "-b:a", "128k", str(target)], check=True, timeout=30)
    with target.open("rb") as stream:
        response = requests.post(BASE + "/api/analysis/sync/audio", files={"file": ("microphone-format.m4a", stream, "audio/mp4")}, timeout=240)
    response.raise_for_status()
    analysis = response.json()
    assert len(analysis["predictions"]) == 3
    assert analysis["modelName"] == "greenarcade/wav2vec2-vd-bird-sound-classification"
    media = requests.get(BASE + analysis["fileUrl"], timeout=30)
    assert media.headers["Content-Type"].startswith("audio/mp4")
    manifest = requests.get("http://127.0.0.1:8081", headers={"expo-platform": "ios", "accept": "application/expo+json"}, timeout=120)
    manifest.raise_for_status()
    payload = manifest.json()
    assert "launchAsset" in payload
    settings = (ROOT / "mobile-app" / ".env").read_text(encoding="utf-8")
    api_url = next(line.partition("=")[2].strip() for line in settings.splitlines() if line.startswith("EXPO_PUBLIC_API_URL="))
    lan = requests.get(api_url.rstrip("/") + "/api/health", timeout=30)
    lan.raise_for_status()
    result = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "mock_used": False, "physical_iphone_tested": False, "audio_source": "original robin.wav transcoded to AAC/M4A; not a device recording", "analysis": analysis, "metro_ios_manifest": {"id": payload.get("id"), "launchAssetUrl": payload["launchAsset"]["url"]}, "lan_api": lan.json()}
    (ROOT / "verification" / "mobile-protocol.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"analysis_id": analysis["id"], "m4a_real_inference": True, "metro_ios_manifest": True, "lan_api": True, "physical_iphone_tested": False}))


if __name__ == "__main__":
    main()
