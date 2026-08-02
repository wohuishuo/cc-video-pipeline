import json
from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "creator-batch"
sys.path.insert(0, str(APP))

from creator_batch.child_pipeline import ProcessResult, PublicMvpItemProcessor
from creator_batch.contracts import BatchPolicy, CreatorItem


def policy():
    return BatchPolicy.create(
        ["ru-RU", "en-US"],
        {"ru-RU": "ru-RU-DmitryNeural", "en-US": "en-US-GuyNeural"},
        source_language="zh",
        asr_model="small",
        asr_device="cpu",
        asr_compute_type="int8",
        translation_device="cpu",
        translation_provider="deepseek",
        translation_batch_size=4,
        source_volume=0.08,
    )


def test_public_processor_calls_each_owner_in_order_with_committed_predecessor_facts(tmp_path):
    calls = []
    manifests = {}

    def runner(argv, on_log):
        calls.append(list(argv))
        launcher = Path(argv[argv.index("-File") + 1]).parent.name
        output = Path(argv[argv.index("--output-dir") + 1])
        output.mkdir(parents=True, exist_ok=True)
        filename = {
            "source-intake": "source-manifest.json",
            "transcription": "transcript-manifest.json",
            "translation": "translation-manifest.json",
            "voice-rendering": "voice-manifest.json",
            "localization": "localization-manifest.json",
        }[launcher]
        manifest = output / filename
        value = {"schemaVersion": 1, "owner": launcher}
        if launcher == "localization":
            value["derivatives"] = [{"path": str(output / "ru.mp4")}, {"path": str(output / "en.mp4")}]
        manifest.write_text(json.dumps(value), encoding="utf-8")
        manifests[launcher] = manifest
        return ProcessResult(0, json.dumps({"resultClass": "COMPLETED", "manifest": str(manifest)}), "")

    item = CreatorItem(1, "video-1", "https://www.douyin.com/video/1", "First", None)
    cookies = tmp_path / "cookies.txt"
    cookies.write_text("cookie", encoding="utf-8")

    result = PublicMvpItemProcessor(tmp_path, runner=runner).process(
        item,
        tmp_path / "item",
        "batch:item:1",
        policy(),
        cookies,
        lambda _line: None,
    )

    assert result.completed
    assert result.localization_manifest == manifests["localization"].resolve()
    assert result.derivative_count == 2
    assert [Path(call[call.index("-File") + 1]).parent.name for call in calls] == [
        "source-intake",
        "transcription",
        "translation",
        "voice-rendering",
        "localization",
    ]
    assert str(manifests["source-intake"].resolve()) in calls[1]
    assert str(manifests["transcription"].resolve()) in calls[2]
    assert str(manifests["translation"].resolve()) in calls[3]
    assert all(str(path.resolve()) in calls[4] for path in (manifests["source-intake"], manifests["translation"], manifests["voice-rendering"]))
    assert calls[0][-4:] == ["--max-height", "1080", "--cookies", str(cookies.resolve())]
    assert calls[2].count("--target-language") == 2
    assert calls[2][calls[2].index("--provider") + 1] == "deepseek"
    assert calls[3].count("--voice") == 2


def test_public_processor_stops_before_successor_when_owner_does_not_commit_manifest(tmp_path):
    calls = []

    def runner(argv, on_log):
        calls.append(list(argv))
        launcher = Path(argv[argv.index("-File") + 1]).parent.name
        if launcher == "source-intake":
            return ProcessResult(0, '{"resultClass":"COMPLETED","manifest":"missing.json"}', "")
        raise AssertionError("a successor ran without a committed Source Manifest")

    result = PublicMvpItemProcessor(tmp_path, runner=runner).process(
        CreatorItem(1, "video-1", "https://www.douyin.com/video/1", "First", None),
        tmp_path / "item",
        "batch:item:1",
        policy(),
        None,
        lambda _line: None,
    )

    assert not result.completed
    assert result.error == "Source Intake did not commit a readable manifest"
    assert len(calls) == 1
