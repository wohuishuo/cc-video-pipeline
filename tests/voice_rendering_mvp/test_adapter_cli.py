import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "apps" / "voice-rendering"
sys.path.insert(0, str(APP))

from .helpers import translation_manifest  # noqa: E402
from voice_rendering_app.adapters import EdgeTtsAdapter  # noqa: E402
from voice_rendering_app.cli import main, parse_voices  # noqa: E402


def test_voice_policy_parser_rejects_duplicates_and_invalid_values():
    assert parse_voices(["ru-RU=ru-RU-DmitryNeural"]) == {"ru-RU": "ru-RU-DmitryNeural"}
    for values in (["bad"], ["ru-RU="], ["ru-RU=a", "ru-RU=b"]):
        try:
            parse_voices(values)
        except ValueError:
            pass
        else:
            raise AssertionError(values)


def test_edge_adapter_invokes_argv_and_requires_probe(tmp_path):
    calls = []
    output = tmp_path / "clip.mp3"

    def runner(argv):
        calls.append(argv)
        output.write_bytes(b"audio")

    adapter = EdgeTtsAdapter(command_runner=runner, duration_probe=lambda path: 1.25)
    duration = adapter.synthesize("Привет", "ru-RU-DmitryNeural", output, lambda _message: None)
    assert duration == 1.25
    assert calls[0][0:3] == [sys.executable, "-m", "edge_tts"]
    assert "--write-media" in calls[0]


class CliAdapter:
    identity = "cli-voice@1"

    def synthesize(self, text, voice, output, on_log):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"voice")
        return 0.5


def test_cli_publishes_machine_result(tmp_path, capsys):
    source = translation_manifest(tmp_path)
    code = main([
        str(source), "--output-dir", str(tmp_path / "out"), "--operation-id", "op-1",
        "--voice", "ru-RU=ru-RU-DmitryNeural", "--voice", "en-US=en-US-GuyNeural", "--json",
    ], adapter_factory=lambda _args: CliAdapter())
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["resultClass"] == "COMPLETED"


def test_public_app_contract_and_help():
    manifest = json.loads((APP / "mvp.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "voice-rendering"
    assert manifest["delivery_level"] == "DOMAIN_VERIFIED"
    assert (APP / manifest["entrypoint"]).is_file()
    assert (APP / manifest["install"]).is_file()
    completed = subprocess.run([sys.executable, "-m", "voice_rendering_app.cli", "--help"], cwd=APP, capture_output=True, text=True)
    assert completed.returncode == 0
    assert "--voice" in completed.stdout
