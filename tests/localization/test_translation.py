import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest


LOCALIZATION_ROOT = Path(__file__).resolve().parents[2] / "apps" / "localization"
sys.path.insert(0, str(LOCALIZATION_ROOT))

from localizer.contracts import JobRecord, Segment, StageRecord, sha256_file  # noqa: E402
from localizer.translation import (  # noqa: E402
    TranslationError,
    build_translation_request,
    merge_translations,
    rewrite_overflow_segments,
    translate_job,
    validate_translations,
)


def source_segments():
    return [
        Segment(1, 0.2, 2.4, "2026年增长10%", []),
        Segment(2, 2.5, 4.0, "工业机器人", []),
        Segment(3, 4.0, 5.25, "产量为25台", []),
    ]


def russian_rows():
    return [
        {"id": 1, "text_ru": "Рост на 10% в 2026 году"},
        {"id": 2, "text_ru": "Промышленные роботы"},
        {"id": 3, "text_ru": "Производство составляет 25 единиц"},
    ]


def test_merge_translation_keeps_timestamps_and_rejects_missing_ids():
    """Dropping a source ID or replacing local timing must fail this boundary."""
    source = source_segments()[:2]

    with pytest.raises(TranslationError, match="missing ids: 2"):
        merge_translations(source, russian_rows()[:1])

    merged = merge_translations(source, russian_rows()[:2])

    assert [(item.id, item.start, item.end) for item in merged] == [
        (1, 0.2, 2.4),
        (2, 2.5, 4.0),
    ]
    assert merged[0].text == "Рост на 10% в 2026 году"


def test_merge_translation_reconstructs_source_order_from_unordered_exact_ids():
    """Positional pairing must not change source timing when the model reorders valid IDs."""
    source = source_segments()[:2]

    merged = merge_translations(source, list(reversed(russian_rows()[:2])))

    assert [(item.id, item.start, item.end, item.text) for item in merged] == [
        (1, 0.2, 2.4, "Рост на 10% в 2026 году"),
        (2, 2.5, 4.0, "Промышленные роботы"),
    ]


@pytest.mark.parametrize(
    "rows, message",
    [
        ([{"id": 1, "text_ru": "Рост 2026"}, {"id": 1, "text_ru": "Роботы"}], "duplicate ids: 1"),
        ([{"id": 1, "text_ru": "Рост 2026"}, {"id": 2, "text_ru": "工业机器人"}], "Chinese characters"),
        ([{"id": 1, "text_ru": "Рост 10"}, {"id": 2, "text_ru": "Роботы"}], "numerals"),
        ([{"id": 1, "text_ru": "Growth 2026"}, {"id": 2, "text_ru": "Robots"}], "Cyrillic"),
    ],
)
def test_validate_translations_rejects_unsafe_model_output(rows, message):
    """Relaxing ID, Chinese, numeral, or Cyrillic checks would ship invalid captions."""
    with pytest.raises(TranslationError, match=message):
        validate_translations(source_segments()[:2], rows)


def test_build_translation_request_is_deterministic_and_excludes_timestamps():
    """Letting the model see or set timing would break the ASR-owned timeline."""
    payload = build_translation_request(source_segments()[:2])

    assert payload["model"] == "qwen3.5:9b"
    assert payload["stream"] is False
    assert payload["think"] is False
    assert payload["options"] == {"temperature": 0, "num_ctx": 4096}
    assert payload["format"] == {
        "type": "object",
        "additionalProperties": False,
        "required": ["translations"],
        "properties": {
            "translations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "text_ru"],
                    "properties": {"id": {"type": "integer"}, "text_ru": {"type": "string"}},
                },
            }
        },
    }
    rows = json.loads(payload["messages"][1]["content"])
    assert rows == [
        {"id": 1, "text_zh": "2026年增长10%"},
        {"id": 2, "text_zh": "工业机器人"},
    ]
    assert "start" not in payload["messages"][1]["content"]
    assert "end" not in payload["messages"][1]["content"]


class OllamaFake:
    def __init__(self):
        self.requests = []
        self.third_chunk_attempts = 0

    def handler(self):
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                assert self.path == "/api/chat"
                request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                fake.requests.append(request)
                rows = json.loads(request["messages"][1]["content"])
                if rows[0]["id"] == 3:
                    fake.third_chunk_attempts += 1
                    if fake.third_chunk_attempts == 1:
                        self.send_response(503)
                        self.end_headers()
                        return
                response = {"message": {"content": json.dumps({"translations": [russian_rows()[row["id"] - 1] for row in rows]}, ensure_ascii=False)}}
                encoded = json.dumps(response, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, *_args):
                pass

        return Handler


def make_job_with_transcript(tmp_path):
    source = tmp_path / "[123] source.mp4"
    source.write_bytes(b"fixture media")
    job = JobRecord(id="123", source=str(source), source_sha256=sha256_file(source))
    artifact_dir = tmp_path / "russian" / "jobs" / job.id
    artifact_dir.mkdir(parents=True)
    transcript = artifact_dir / "transcript.zh.json"
    transcript.write_text(
        json.dumps({"schema_version": 1, "segments": [segment.to_dict() for segment in source_segments()]}, ensure_ascii=False),
        encoding="utf-8",
    )
    job.stages["transcription"] = StageRecord.completed(
        adapter="faster-whisper@large-v3",
        inputs={"source_sha256": job.source_sha256},
        outputs={"transcript": str(transcript)},
    )
    return job, artifact_dir


def test_translate_job_retries_only_failed_chunk_and_writes_exact_srt_timing(tmp_path):
    """Retrying all chunks or model-supplied timecodes would duplicate work or drift captions."""
    fake = OllamaFake()
    server = ThreadingHTTPServer(("127.0.0.1", 0), fake.handler())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    job, artifact_dir = make_job_with_transcript(tmp_path)
    try:
        result = translate_job(
            job,
            ollama_base_url=f"http://127.0.0.1:{server.server_port}",
            chunk_size=2,
        )
    finally:
        server.shutdown()
        thread.join()

    assert fake.third_chunk_attempts == 2
    assert [json.loads(item["messages"][1]["content"])[0]["id"] for item in fake.requests] == [1, 3, 3]
    assert all(item["model"] == "qwen3.5:9b" and item["think"] is False for item in fake.requests)
    assert result["segments"] == [
        {"id": 1, "start": 0.2, "end": 2.4, "text_ru": "Рост на 10% в 2026 году"},
        {"id": 2, "start": 2.5, "end": 4.0, "text_ru": "Промышленные роботы"},
        {"id": 3, "start": 4.0, "end": 5.25, "text_ru": "Производство составляет 25 единиц"},
    ]
    assert (artifact_dir / "subtitles.ru.srt").read_text(encoding="utf-8") == (
        "1\n00:00:00,200 --> 00:00:02,400\nРост на 10% в 2026 году\n\n"
        "2\n00:00:02,500 --> 00:00:04,000\nПромышленные роботы\n\n"
        "3\n00:00:04,000 --> 00:00:05,250\nПроизводство составляет 25 единиц\n\n"
    )
    assert set(job.stages) == {"transcription", "translation"}
    assert job.stages["translation"].status == "completed"


def test_translate_job_rejects_wrong_transcript_schema_without_artifacts(tmp_path):
    """Accepting an unknown transcript schema could silently reinterpret ASR output."""
    job, artifact_dir = make_job_with_transcript(tmp_path)
    transcript = artifact_dir / "transcript.zh.json"
    transcript.write_text('{"schema_version": 2, "segments": []}', encoding="utf-8")

    with pytest.raises(TranslationError, match="schema version"):
        translate_job(job, http_post=lambda *_args: {})

    assert job.stages["translation"].status == "failed"
    assert not (artifact_dir / "translation.ru.json").exists()
    assert not (artifact_dir / "subtitles.ru.srt").exists()


def test_rewrite_overflow_segments_sends_current_russian_text_and_duration_constraint():
    """A rewrite must shorten the prior Russian text, never freshly translate Chinese text."""
    source = source_segments()[:1]
    current = merge_translations(source, russian_rows()[:1])
    requests = []

    def rewritten(_url, payload):
        requests.append(payload)
        return {"message": {"content": '{"translations": [{"id": 1, "text_ru": "Рост 10% в 2026"}]}'}}

    result = rewrite_overflow_segments(source, [1], current, http_post=rewritten)

    rows = json.loads(requests[0]["messages"][1]["content"])
    assert rows == [{"id": 1, "text_ru": "Рост на 10% в 2026 году", "max_duration_seconds": 2.2}]
    assert "start" not in requests[0]["messages"][1]["content"]
    assert "end" not in requests[0]["messages"][1]["content"]
    assert result == [type(current[0])(1, 0.2, 2.4, "Рост 10% в 2026")]
