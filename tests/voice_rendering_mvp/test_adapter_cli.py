import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "apps" / "voice-rendering"
sys.path.insert(0, str(APP))

from .helpers import translation_manifest  # noqa: E402
from voice_rendering_app.adapters import (  # noqa: E402
    EdgeTtsAdapter,
    OriginalAudioAdapter,
    Qwen3TtsAdapter,
)
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
    duration = adapter.synthesize(
        "Привет", "ru-RU", "ru-RU-DmitryNeural", output, lambda _message: None
    )
    assert duration == 1.25
    assert calls[0][0:3] == [sys.executable, "-m", "edge_tts"]
    assert "--write-media" in calls[0]


class CliAdapter:
    identity = "cli-voice@1"
    output_suffix = ".wav"

    def synthesize(self, text, language, voice, output, on_log, *, target_duration=None):
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


def test_cli_selects_an_explicit_voice_provider(tmp_path):
    seen = []

    def factory(args):
        seen.append((args.provider, args.qwen_device))
        return CliAdapter()

    code = main([
        str(translation_manifest(tmp_path)), "--output-dir", str(tmp_path / "provider-out"),
        "--operation-id", "provider-op", "--provider", "qwen3", "--qwen-device", "cpu",
        "--voice", "ru-RU=Ryan", "--voice", "en-US=Aiden", "--json",
    ], adapter_factory=factory)

    assert code == 0
    assert seen == [("qwen3", "cpu")]


def test_qwen3_adapter_keeps_one_engine_and_writes_provider_audio(tmp_path):
    calls = []

    class Engine:
        def load(self):
            calls.append("load")

        def synth_preset(self, text, language, speaker):
            calls.append((text, language, speaker))
            return [0.0, 0.25, -0.25, 0.0], 4

    def writer(path, audio, sample_rate):
        calls.append((Path(path).suffixes, len(audio), sample_rate))
        Path(path).write_bytes(b"wav")

    adapter = Qwen3TtsAdapter(engine_factory=Engine, audio_writer=writer)
    first = adapter.synthesize(
        "Привет", "ru-RU", "Ryan", tmp_path / "one.wav", lambda _line: None
    )
    second = adapter.synthesize(
        "Hello", "en-US", "Aiden", tmp_path / "two.wav", lambda _line: None
    )

    assert adapter.output_suffix == ".wav"
    assert (first, second) == (1.0, 1.0)
    assert calls.count("load") == 1
    assert ("Привет", "ru", "Ryan") in calls
    assert ("Hello", "en", "Aiden") in calls


def test_original_audio_adapter_generates_exact_segment_silence(tmp_path):
    commands = []

    def runner(argv):
        commands.append(argv)
        Path(argv[-1]).write_bytes(b"wav")

    adapter = OriginalAudioAdapter(command_runner=runner)
    output = tmp_path / "silence.wav"
    duration = adapter.synthesize(
        "translated", "ru-RU", "original-audio", output, lambda _line: None,
        target_duration=2.75,
    )

    assert duration == 2.75
    assert adapter.output_suffix == ".wav"
    assert "2.750000" in commands[0]
    assert output.read_bytes() == b"wav"


def test_public_app_contract_and_help():
    manifest = json.loads((APP / "mvp.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "voice-rendering"
    assert manifest["delivery_level"] == "DOMAIN_VERIFIED"
    assert (APP / manifest["entrypoint"]).is_file()
    assert (APP / manifest["install"]).is_file()
    completed = subprocess.run([sys.executable, "-m", "voice_rendering_app.cli", "--help"], cwd=APP, capture_output=True, text=True)
    assert completed.returncode == 0
    assert "--voice" in completed.stdout
    assert "--provider" in completed.stdout
