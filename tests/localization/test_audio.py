import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import wave

import pytest


LOCALIZATION_ROOT = Path(__file__).resolve().parents[2] / "apps" / "localization"
sys.path.insert(0, str(LOCALIZATION_ROOT))

from localizer.audio import (  # noqa: E402
    AudioMixError,
    AudioMixSpec,
    build_mix,
    classify_fit,
    _atempo_filters,
    _final_mix_filter,
)


def test_extreme_tempo_is_split_into_supported_ffmpeg_filters():
    assert _atempo_filters(250.0) == ["atempo=100.000000000", "atempo=2.500000000"]


def test_final_mix_makes_narration_dominant_over_background():
    graph = _final_mix_filter(10.0)
    assert "volume=0.25[bed]" in graph
    assert "volume=2.5[voice]" in graph
from localizer.contracts import sha256_file  # noqa: E402


FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")


def write_tone(
    path: Path,
    *,
    seconds: float,
    frequency: float,
    sample_rate: int,
    channels: int,
    amplitude: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(seconds * sample_rate)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(channels)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        samples = bytearray()
        for index in range(frames):
            value = int(amplitude * math.sin(2 * math.pi * frequency * index / sample_rate))
            samples.extend(struct.pack("<h", value) * channels)
        output.writeframes(samples)


def build_audio_fixture(tmp_path: Path, *, duration: float = 3.0) -> AudioMixSpec:
    clip_dir = tmp_path / "voice" / "clips"
    write_tone(
        clip_dir / "0001.wav",
        seconds=1.0,
        frequency=880.0,
        sample_rate=24_000,
        channels=1,
        amplitude=12_000,
    )
    instrumental = tmp_path / "audio" / "no_vocals.wav"
    write_tone(
        instrumental,
        seconds=duration,
        frequency=220.0,
        sample_rate=48_000,
        channels=2,
        amplitude=5_000,
    )
    return AudioMixSpec(
        segments=[{"id": 1, "start": 0.75, "end": 1.75, "text_ru": "Тест"}],
        clip_dir=clip_dir,
        instrumental_path=instrumental,
        source_duration=duration,
        output_dir=instrumental.parent,
    )


def ffprobe_json(path: Path) -> dict:
    completed = subprocess.run(
        [
            FFPROBE,
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_type,channels,sample_rate",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return json.loads(completed.stdout)


def read_channel(path: Path) -> tuple[int, list[int]]:
    with wave.open(str(path), "rb") as source:
        assert source.getsampwidth() == 2
        sample_rate = source.getframerate()
        channels = source.getnchannels()
        values = struct.unpack(f"<{source.getnframes() * channels}h", source.readframes(source.getnframes()))
    return sample_rate, list(values[::channels])


def rms(samples: list[int], sample_rate: int, start: float, end: float) -> float:
    window = samples[int(start * sample_rate) : int(end * sample_rate)]
    return math.sqrt(sum(value * value for value in window) / len(window))


def tone_amplitude(
    samples: list[int], sample_rate: int, frequency: float, start: float, end: float
) -> float:
    window = samples[int(start * sample_rate) : int(end * sample_rate)]
    sin_part = sum(
        value * math.sin(2 * math.pi * frequency * index / sample_rate)
        for index, value in enumerate(window)
    )
    cos_part = sum(
        value * math.cos(2 * math.pi * frequency * index / sample_rate)
        for index, value in enumerate(window)
    )
    return 2 * math.hypot(sin_part, cos_part) / len(window)


def require_ffmpeg() -> None:
    if FFMPEG is None or FFPROBE is None:
        pytest.skip("FFmpeg fixture tools are unavailable")


def test_alignment_flags_more_than_35_percent_compression():
    """Raising or removing the cap would force unintelligible speech into a fixed slot."""
    assert classify_fit(tts_seconds=4.1, slot_seconds=3.0) == "rewrite"
    assert classify_fit(tts_seconds=4.1, slot_seconds=3.0, max_compression_ratio=2.0) == "compress"
    assert classify_fit(tts_seconds=3.9, slot_seconds=3.0) == "compress"
    assert classify_fit(tts_seconds=3.0, slot_seconds=3.0) == "fit"


def test_mix_matches_source_duration_and_has_stereo_audio(tmp_path):
    """Omitting the final trim/pad or stereo conversion would break the render contract."""
    require_ffmpeg()
    result = build_mix(build_audio_fixture(tmp_path, duration=3.0))

    probe = ffprobe_json(result.mix_path)

    assert result.overflow_ids == ()
    assert abs(float(probe["format"]["duration"]) - 3.0) < 0.05
    audio_streams = [row for row in probe["streams"] if row["codec_type"] == "audio"]
    assert audio_streams[0]["channels"] == 2
    assert audio_streams[0]["sample_rate"] == "48000"


def test_narration_uses_source_timeline_silence_and_compresses_only_within_cap(tmp_path):
    """Concatenating clips without their leading gap would shift Russian speech off picture."""
    require_ffmpeg()
    spec = build_audio_fixture(tmp_path)
    clip = spec.clip_dir / "0001.wav"
    write_tone(
        clip,
        seconds=1.3,
        frequency=880.0,
        sample_rate=24_000,
        channels=1,
        amplitude=12_000,
    )

    result = build_mix(spec)
    sample_rate, samples = read_channel(result.narration_path)
    receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))

    assert rms(samples, sample_rate, 0.10, 0.60) < 1
    assert rms(samples, sample_rate, 0.90, 1.40) > 1_000
    assert rms(samples, sample_rate, 2.00, 2.50) < 1
    assert receipt["segments"][0]["fit"] == "compress"
    assert receipt["segments"][0]["tempo"] == pytest.approx(1.3, abs=0.001)


def test_overflow_ids_are_returned_without_publishing_or_mixing(tmp_path):
    """Processing even one overflow would hide the required concise-rewrite gate."""
    require_ffmpeg()
    spec = build_audio_fixture(tmp_path)
    write_tone(
        spec.clip_dir / "0001.wav",
        seconds=1.36,
        frequency=880.0,
        sample_rate=24_000,
        channels=1,
        amplitude=12_000,
    )

    result = build_mix(spec)

    assert result.overflow_ids == (1,)
    assert result.published is False
    assert not result.narration_path.exists()
    assert not result.mix_path.exists()
    assert not result.receipt_path.exists()
    assert not list(spec.output_dir.glob(".mix-staging-*"))


def test_mix_retains_and_ducks_bed_and_records_measured_loudness(tmp_path):
    """Dropping the bed, ducking sidechain, or final meter would violate mix acceptance."""
    require_ffmpeg()
    result = build_mix(build_audio_fixture(tmp_path))
    sample_rate, samples = read_channel(result.mix_path)
    quiet_bed = tone_amplitude(samples, sample_rate, 220.0, 0.15, 0.55)
    bed_under_voice = tone_amplitude(samples, sample_rate, 220.0, 0.95, 1.45)
    receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))

    assert quiet_bed > 100
    assert bed_under_voice < quiet_bed * 0.75
    assert receipt["loudness"]["integrated_lufs"] == pytest.approx(-16.0, abs=1.0)
    assert receipt["loudness"]["true_peak_dbtp"] <= -1.4
    assert receipt["outputs"]["mix"]["sha256"] == sha256_file(result.mix_path)


def test_invalid_retry_leaves_no_partial_files_and_preserves_prior_publish(tmp_path):
    """A failed retry must not replace a complete mix or expose temporary media as final."""
    require_ffmpeg()
    spec = build_audio_fixture(tmp_path)
    first = build_mix(spec)
    prior_hashes = {
        path.name: sha256_file(path)
        for path in (first.narration_path, first.mix_path, first.receipt_path)
    }
    (spec.clip_dir / "0001.wav").unlink()

    with pytest.raises(AudioMixError, match="missing or empty voice clip"):
        build_mix(spec)

    assert {
        path.name: sha256_file(path)
        for path in (first.narration_path, first.mix_path, first.receipt_path)
    } == prior_hashes
    assert not list(spec.output_dir.glob(".mix-staging-*"))


def test_invalid_timing_and_source_duration_are_rejected_before_ffmpeg(tmp_path):
    """Non-finite or out-of-source slots would make duration alignment undefined."""
    spec = build_audio_fixture(tmp_path)
    spec.source_duration = 0.0
    with pytest.raises(AudioMixError, match="source duration"):
        build_mix(spec)

    spec = build_audio_fixture(tmp_path / "late")
    spec.segments = [{"id": 1, "start": 2.5, "end": 3.5, "text_ru": "Тест"}]
    with pytest.raises(AudioMixError, match="source duration"):
        build_mix(spec)
