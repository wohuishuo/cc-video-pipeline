import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest


LOCALIZATION_ROOT = Path(__file__).resolve().parents[2] / "apps" / "localization"
sys.path.insert(0, str(LOCALIZATION_ROOT))

from localizer.asr import TranscriptionError, transcribe_batch, transcribe_job  # noqa: E402
from localizer.contracts import JobRecord, sha256_file  # noqa: E402


@dataclass
class FakeWord:
    start: float
    end: float
    word: str


@dataclass
class FakeSegment:
    start: float
    end: float
    text: str
    words: list[FakeWord]


class FakeWhisperModel:
    def __init__(self, segments, error=None):
        self.segments = segments
        self.error = error
        self.calls = []

    def transcribe(self, source, **kwargs):
        self.calls.append((source, kwargs))
        if self.error is not None:
            raise self.error
        return iter(self.segments), object()


def make_job(tmp_path, video_id="123"):
    source = tmp_path / f"[{video_id}] source.mp4"
    source.write_bytes(b"fixture media")
    return JobRecord(id=video_id, source=str(source), source_sha256=sha256_file(source))


def test_transcribe_job_preserves_word_timestamps(tmp_path):
    """Dropping or changing a model word timestamp must fail this contract."""
    fake = FakeWhisperModel(
        [
            FakeSegment(
                0.5,
                2.0,
                "工业机器人",
                [FakeWord(0.5, 1.0, "工业"), FakeWord(1.0, 2.0, "机器人")],
            )
        ]
    )

    result = transcribe_job(fake, make_job(tmp_path))

    assert result["segments"][0] == {
        "id": 1,
        "start": 0.5,
        "end": 2.0,
        "text": "工业机器人",
        "words": [
            {"start": 0.5, "end": 1.0, "word": "工业"},
            {"start": 1.0, "end": 2.0, "word": "机器人"},
        ],
    }
    assert fake.calls == [
        (
            str(tmp_path / "[123] source.mp4"),
            {
                "language": "zh",
                "word_timestamps": True,
                "vad_filter": True,
                "condition_on_previous_text": True,
            },
        )
    ]


def test_transcribe_job_preserves_model_text_without_normalizing_it(tmp_path):
    """Trimming model text would silently rewrite the authoritative transcript."""
    fake = FakeWhisperModel(
        [FakeSegment(0.0, 1.0, " 工业", [FakeWord(0.0, 1.0, " 工业")])]
    )

    result = transcribe_job(fake, make_job(tmp_path))

    assert result["segments"][0]["text"] == " 工业"
    assert result["segments"][0]["words"][0]["word"] == " 工业"


def test_importing_adapter_does_not_import_faster_whisper():
    """Injected-model tests must stay offline and avoid any model download/import."""
    assert "faster_whisper" not in sys.modules


def test_transcribe_job_writes_owned_artifacts_and_only_its_stage(tmp_path):
    """Writing a transcript must not alter a different adapter's receipt."""
    job = make_job(tmp_path)
    fake = FakeWhisperModel([FakeSegment(0.0, 1.0, "测试", [FakeWord(0.0, 1.0, "测试")])])
    job.stages["translation"] = object()

    transcribe_job(fake, job)

    artifact_dir = tmp_path / "russian" / "jobs" / job.id
    transcript = artifact_dir / "transcript.zh.json"
    srt = artifact_dir / "transcript.zh.srt"
    assert json.loads(transcript.read_text(encoding="utf-8"))["segments"][0]["text"] == "测试"
    assert srt.read_text(encoding="utf-8") == "1\n00:00:00,000 --> 00:00:01,000\n测试\n\n"
    assert set(job.stages) == {"translation", "transcription"}
    assert job.stages["translation"] is not None
    assert job.stages["transcription"].status == "completed"
    assert set(job.stages["transcription"].outputs) == {"transcript", "srt"}


@pytest.mark.parametrize(
    "segments, message",
    [
        ([], "empty transcript"),
        ([FakeSegment(1.0, 1.0, "测试", [])], "positive duration"),
        ([FakeSegment(1.0, 2.0, "", [])], "non-empty text"),
        (
            [
                FakeSegment(1.0, 2.0, "第一", []),
                FakeSegment(1.5, 3.0, "第二", []),
            ],
            "ordered",
        ),
        (
            [FakeSegment(0.0, 1.0, "测试", [FakeWord(0.0, 1.1, "测试")])],
            "within segment",
        ),
    ],
)
def test_transcribe_job_rejects_invalid_transcript_before_artifact_write(
    tmp_path, segments, message
):
    """Removing ASR sanity validation must leave invalid timing on disk."""
    job = make_job(tmp_path)

    with pytest.raises(TranscriptionError, match=message):
        transcribe_job(FakeWhisperModel(segments), job)

    artifact_dir = tmp_path / "russian" / "jobs" / job.id
    assert not (artifact_dir / "transcript.zh.json").exists()
    assert not (artifact_dir / "transcript.zh.srt").exists()
    assert job.stages["transcription"].status == "failed"


def test_transcribe_job_marks_model_error_failed_without_partial_outputs(tmp_path):
    """A model exception must not leave a completed receipt or partial transcript."""
    job = make_job(tmp_path)

    with pytest.raises(RuntimeError, match="CUDA failure"):
        transcribe_job(FakeWhisperModel([], error=RuntimeError("CUDA failure")), job)

    artifact_dir = tmp_path / "russian" / "jobs" / job.id
    assert job.stages["transcription"].status == "failed"
    assert not (artifact_dir / "transcript.zh.json").exists()
    assert not (artifact_dir / "transcript.zh.srt").exists()


def test_transcribe_job_can_retry_a_failed_stage(tmp_path):
    """Leaving a failed receipt terminal would prevent recovery after a model retry."""
    job = make_job(tmp_path)

    with pytest.raises(RuntimeError, match="temporary CUDA failure"):
        transcribe_job(
            FakeWhisperModel([], error=RuntimeError("temporary CUDA failure")), job
        )
    transcript = transcribe_job(
        FakeWhisperModel([FakeSegment(0.0, 1.0, "恢复", [FakeWord(0.0, 1.0, "恢复")])]),
        job,
    )

    assert transcript["segments"][0]["text"] == "恢复"
    assert job.stages["transcription"].status == "completed"


def test_transcribe_batch_loads_one_cuda_model_and_continues_after_a_failed_job(tmp_path):
    """Creating a model per job or aborting retryable jobs breaks GPU residency."""
    first = make_job(tmp_path, "111")
    second = make_job(tmp_path, "222")
    created = []

    class RoutingModel(FakeWhisperModel):
        def transcribe(self, source, **kwargs):
            self.calls.append((source, kwargs))
            if "[111]" in source:
                raise RuntimeError("bad source")
            return iter([FakeSegment(0.0, 1.0, "测试", [FakeWord(0.0, 1.0, "测试")])]), object()

    def factory(model_name, *, device, compute_type):
        created.append((model_name, device, compute_type))
        return RoutingModel([])

    results = transcribe_batch([first, second], model_factory=factory)

    assert created == [("large-v3", "cuda", "float16")]
    assert [result["job_id"] for result in results] == ["222"]
    assert first.stages["transcription"].status == "failed"
    assert second.stages["transcription"].status == "completed"
