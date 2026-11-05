import subprocess
import tempfile
from pathlib import Path

from birdlab.config import MAX_AUDIO_BYTES
from birdlab.errors import InputError
from birdlab.files import load_audio, validate_size


def decode_audio(data: bytes, name: str):
    validate_size(data, MAX_AUDIO_BYTES)
    suffix = Path(name).suffix.lower()
    if suffix in {".wav", ".mp3", ".flac"}:
        return load_audio(data, name)
    if suffix not in {".m4a", ".aac", ".ogg"}:
        raise InputError("Підтримуються WAV, MP3, FLAC, M4A, AAC та OGG.")
    import imageio_ffmpeg

    try:
        with tempfile.TemporaryDirectory(prefix="bird-audio-") as folder:
            source = Path(folder) / f"input{suffix}"
            source.write_bytes(data)
            converted = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-nostdin", "-v", "error", "-protocol_whitelist", "file,pipe", "-i", str(source), "-vn", "-t", "61", "-ac", "1", "-ar", "16000", "-f", "wav", "pipe:1"], capture_output=True, timeout=30, check=True)
            return load_audio(converted.stdout, "converted.wav")
    except (OSError, subprocess.SubprocessError) as exc:
        raise InputError("Не вдалося декодувати аудіозапис. Виберіть коректний файл до 60 секунд.") from exc
