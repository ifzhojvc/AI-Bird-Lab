import io

import numpy as np
import pytest
import soundfile as sf
from PIL import Image

from birdlab.errors import InputError
from birdlab.files import load_audio, load_image, read_file, save_upload, validate_size


@pytest.mark.parametrize("name", ["птах.png", "PHOTO.PNG", "folder name/птах.png"])
def test_valid_png(png_bytes, name):
    image = load_image(png_bytes, name)
    assert image.mode == "RGB" and image.size == (40, 30)


@pytest.mark.parametrize("extension", ["jpg", "jpeg", "JPG"])
def test_valid_jpeg(extension):
    stream = io.BytesIO()
    Image.new("RGB", (10, 10)).save(stream, "JPEG")
    assert load_image(stream.getvalue(), "bird." + extension).size == (10, 10)


@pytest.mark.parametrize("name", ["bird.webp", "bird.gif", "bird.exe", "bird"])
def test_reject_unsupported_image(png_bytes, name):
    with pytest.raises(InputError, match="JPG"):
        load_image(png_bytes, name)


def test_extension_mismatch(png_bytes):
    with pytest.raises(InputError, match="розширенню"):
        load_image(png_bytes, "bird.jpg")


@pytest.mark.parametrize("content", [b"broken image", b"\x89PNG\r\n\x1a\n", b""])
def test_corrupt_or_empty(content):
    with pytest.raises(InputError):
        load_image(content, "bird.png")


def test_transparent_png_composites_white():
    stream = io.BytesIO()
    Image.new("RGBA", (2, 2), (0, 0, 0, 0)).save(stream, "PNG")
    assert load_image(stream.getvalue(), "bird.png").getpixel((0, 0)) == (255, 255, 255)


def test_exif_orientation():
    image = Image.new("RGB", (20, 10))
    exif = image.getexif()
    exif[274] = 6
    stream = io.BytesIO()
    image.save(stream, "JPEG", exif=exif)
    assert load_image(stream.getvalue(), "bird.jpeg").size == (10, 20)


def test_size_limit():
    with pytest.raises(InputError, match="завеликий"):
        validate_size(b"abc", 2)


def test_pixel_limit(monkeypatch, png_bytes):
    monkeypatch.setattr("birdlab.files.MAX_IMAGE_PIXELS", 100)
    with pytest.raises(InputError, match="25 мільйонів"):
        load_image(png_bytes, "bird.png")


def test_missing_file(tmp_path):
    with pytest.raises(InputError, match="прочитати"):
        read_file(tmp_path / "missing.jpg")


def test_save_upload_uses_generated_names(tmp_path, png_bytes):
    first = save_upload(png_bytes, "../../outside.png", tmp_path)
    second = save_upload(png_bytes, "../../outside.png", tmp_path)
    assert first.parent == tmp_path and second != first and first.read_bytes() == png_bytes


def test_stereo_audio_resampling(wav_bytes):
    audio = load_audio(wav_bytes, "спів.wav")
    assert audio.original_channels == 2 and audio.original_rate == 22050
    assert audio.sample_rate == 16000 and audio.samples.ndim == 1
    assert len(audio.samples) == 16000 and audio.duration == 1
    assert audio.samples.dtype == np.float32


@pytest.mark.parametrize("content,name", [(b"", "bird.wav"), (b"bad wave", "bird.wav"), (b"bad", "bird.mp3"), (b"a", "bird.aac")])
def test_invalid_audio(content, name):
    with pytest.raises(InputError):
        load_audio(content, name)


def test_audio_format_mismatch(wav_bytes):
    with pytest.raises(InputError, match="розширенню"):
        load_audio(wav_bytes, "bird.flac")


@pytest.mark.parametrize("seconds", [0.1, 61])
def test_audio_duration_limit(seconds):
    stream = io.BytesIO()
    sf.write(stream, np.ones(int(8000 * seconds)), 8000, format="WAV")
    with pytest.raises(InputError, match="Тривалість"):
        load_audio(stream.getvalue(), "bird.wav")


def test_silent_audio():
    stream = io.BytesIO()
    sf.write(stream, np.zeros(16000), 16000, format="WAV")
    with pytest.raises(InputError, match="тишу"):
        load_audio(stream.getvalue(), "silence.wav")


def test_flac(wav_bytes):
    source = load_audio(wav_bytes, "bird.wav")
    stream = io.BytesIO()
    sf.write(stream, source.samples, 16000, format="FLAC")
    assert load_audio(stream.getvalue(), "bird.flac").sample_rate == 16000


def test_mp3_decoder(wav_bytes):
    if "MP3" not in sf.available_formats():
        pytest.skip("Встановлений libsndfile не підтримує MP3")
    source = load_audio(wav_bytes, "bird.wav")
    stream = io.BytesIO()
    sf.write(stream, source.samples, 16000, format="MP3")
    assert load_audio(stream.getvalue(), "bird.mp3").duration >= 0.25
