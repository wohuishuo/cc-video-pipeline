import json
from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "translation"
sys.path.insert(0, str(APP))

from .helpers import write_transcript_manifest  # noqa: E402
from translation_app.operation import TranslationLoop  # noqa: E402


class FakeAdapter:
    identity = "fake-translation@1"

    def __init__(self, failures=()):
        self.failures = set(failures)
        self.calls = []
        self.active = 0
        self.maximum_active = 0

    def translate(self, texts, source_language, target_language, on_log):
        key = (target_language, texts[0])
        self.calls.append(key)
        self.active += 1
        self.maximum_active = max(self.maximum_active, self.active)
        try:
            if key in self.failures:
                raise RuntimeError(f"failed {key}")
            on_log(f"fake translation {target_language}")
            return tuple(f"{target_language}:{text}" for text in texts)
        finally:
            self.active -= 1


def test_loop_publishes_language_major_items_serially(tmp_path):
    transcript = write_transcript_manifest(tmp_path)
    adapter = FakeAdapter()

    result = TranslationLoop().execute(
        transcript,
        tmp_path / "out",
        "op-1",
        target_languages=["ru-RU", "en-US"],
        adapter=adapter,
    )

    assert result.result_class == "COMPLETED"
    assert adapter.calls == [
        ("ru-RU", "你好世界"),
        ("ru-RU", "第二条"),
        ("en-US", "你好世界"),
        ("en-US", "第二条"),
    ]
    assert adapter.maximum_active == 1
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["targetLanguages"] == ["ru-RU", "en-US"]
    assert [(row["targetLanguage"], row["mediaId"]) for row in manifest["translations"]] == [
        ("ru-RU", "media-a"), ("ru-RU", "media-b"),
        ("en-US", "media-a"), ("en-US", "media-b"),
    ]
    document = json.loads(Path(manifest["translations"][0]["translationPath"]).read_text(encoding="utf-8"))
    assert document["segments"][0]["sourceText"] == "你好世界"
    assert document["segments"][0]["translatedText"] == "ru-RU:你好世界"


def test_failure_is_explicit_and_retry_reuses_other_completed_items(tmp_path):
    transcript = write_transcript_manifest(tmp_path)
    output = tmp_path / "out"
    first = FakeAdapter({("ru-RU", "你好世界")})

    failed = TranslationLoop().execute(
        transcript, output, "op-1", target_languages=["ru-RU"], adapter=first
    )

    assert failed.result_class == "FAILED"
    assert failed.manifest_path is None
    receipt = json.loads(failed.receipt_path.read_text(encoding="utf-8"))
    assert [row["status"] for row in receipt["items"]] == ["FAILED", "COMPLETED"]

    retry = FakeAdapter()
    completed = TranslationLoop().execute(
        transcript, output, "op-1", target_languages=["ru-RU"], adapter=retry
    )
    assert completed.result_class == "COMPLETED"
    assert retry.calls == [("ru-RU", "你好世界")]


def test_completed_operation_replays_and_changed_input_conflicts(tmp_path):
    transcript = write_transcript_manifest(tmp_path)
    output = tmp_path / "out"
    TranslationLoop().execute(
        transcript, output, "op-1", target_languages=["ru-RU"], adapter=FakeAdapter()
    )
    replay_adapter = FakeAdapter()

    replay = TranslationLoop().execute(
        transcript, output, "op-1", target_languages=["ru-RU"], adapter=replay_adapter
    )
    conflict = TranslationLoop().execute(
        transcript, output, "op-1", target_languages=["en-US"], adapter=FakeAdapter()
    )

    assert replay.result_class == "DUPLICATE_COMPLETED"
    assert replay_adapter.calls == []
    assert conflict.result_class == "REJECTED_CONFLICT"
