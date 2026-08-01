import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "apps" / "transcription"
sys.path.insert(0, str(APP))

from transcription_app.adapters import FasterWhisperAdapter  # noqa: E402
from transcription_app.cli import main  # noqa: E402
from transcription_app.contracts import Segment  # noqa: E402
from transcription_app.operation import AdapterTranscript  # noqa: E402


class SegmentRow:
    def __init__(self, start, end, text):
        self.start = start
        self.end = end
        self.text = text


class Info:
    language = "zh"


class FakeModel:
    def transcribe(self, path, **options):
        assert Path(path).is_file()
        assert options["language"] is None
        assert options["vad_filter"] is True
        return iter([SegmentRow(0, 1.25, " 你好 "), SegmentRow(1.25, 2.0, "世界")]), Info()


def test_faster_whisper_adapter_is_lazy_and_normalizes_contract(tmp_path):
    created = []

    def factory(model, **options):
        created.append((model, options))
        return FakeModel()

    adapter = FasterWhisperAdapter("tiny", device="cpu", compute_type="int8", model_factory=factory)
    media = type("Media", (), {"id": "m1", "path": str(tmp_path / "a.mp4")})()
    Path(media.path).write_bytes(b"media")

    transcript = adapter.transcribe(media, "auto", lambda _message: None)

    assert created == [("tiny", {"device": "cpu", "compute_type": "int8"})]
    assert transcript.detected_language == "zh"
    assert [row.text for row in transcript.segments] == ["你好", "世界"]
    assert adapter.identity == "faster-whisper@1:model=tiny:device=cpu:compute=int8"


class CliFakeAdapter:
    identity = "fixture@1"

    def transcribe(self, media, language, on_log):
        return AdapterTranscript("en", (Segment(1, 0, 1, "hello"),))


def test_cli_executes_injected_adapter_and_prints_machine_result(tmp_path, capsys):
    media = tmp_path / "a.mp4"
    media.write_bytes(b"media")
    source = tmp_path / "source-manifest.json"
    source.write_text(
        json.dumps({
            "schemaVersion": 1,
            "sourceKind": "folder",
            "source": {},
            "media": [{"id": "m1", "path": str(media), "size": 5, "extension": ".mp4"}],
        }),
        encoding="utf-8",
    )

    exit_code = main(
        [str(source), "--output-dir", str(tmp_path / "out"), "--operation-id", "op-1", "--json"],
        adapter_factory=lambda _args: CliFakeAdapter(),
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["resultClass"] == "COMPLETED"
    assert Path(output["manifest"]).is_file()


def test_public_app_manifest_readme_and_help_are_complete():
    manifest = json.loads((APP / "mvp.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "transcription"
    assert manifest["delivery_level"] == "DOMAIN_VERIFIED"
    assert "source manifest" in " ".join(manifest["inputs"]).lower()
    assert "transcript-manifest.json" in manifest["outputs"]
    assert (APP / manifest["entrypoint"]).is_file()
    assert (APP / manifest["install"]).is_file()
    readme = (APP / "README.md").read_text(encoding="utf-8").lower()
    assert "one media item at a time" in readme
    assert "translation" in readme and "does not" in readme

    completed = subprocess.run(
        [sys.executable, "-m", "transcription_app.cli", "--help"],
        cwd=APP,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert completed.returncode == 0
    assert "--model" in completed.stdout
    assert "--device" in completed.stdout
