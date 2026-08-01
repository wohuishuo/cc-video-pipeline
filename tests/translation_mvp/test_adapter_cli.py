import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "apps" / "translation"
sys.path.insert(0, str(APP))

from .helpers import write_transcript_manifest  # noqa: E402
from translation_app.adapters import NllbAdapter  # noqa: E402
from translation_app.cli import main  # noqa: E402


class FakeBatch(dict):
    def __init__(self):
        super().__init__({"input_ids": [[1], [2]]})

    def to(self, _device):
        return self


class FakeTokenizer:
    def __init__(self):
        self.src_lang = None
        self.inputs = []

    def __call__(self, texts, **_options):
        self.inputs.append(tuple(texts))
        return FakeBatch()

    def convert_tokens_to_ids(self, code):
        return {"rus_Cyrl": 10, "eng_Latn": 20}[code]

    def batch_decode(self, _rows, skip_special_tokens):
        assert skip_special_tokens
        return ["translated one", "translated two"]


class FakeModel:
    def __init__(self):
        self.forced = []

    def generate(self, **options):
        self.forced.append(options["forced_bos_token_id"])
        return [[1], [2]]


def test_nllb_adapter_maps_public_languages_and_is_lazy():
    tokenizer = FakeTokenizer()
    model = FakeModel()
    created = []

    def factory(model_id, source_code, device):
        created.append((model_id, source_code, device))
        tokenizer.src_lang = source_code
        return tokenizer, model

    adapter = NllbAdapter("local/model", device="cpu", batch_size=8, runtime_factory=factory)

    translated = adapter.translate(("你好", "世界"), "zh", "ru-RU", lambda _message: None)

    assert translated == ("translated one", "translated two")
    assert created == [("local/model", "zho_Hans", "cpu")]
    assert model.forced == [10]
    assert adapter.identity == "nllb@1:model=local/model:device=cpu:batch=8"


class CliAdapter:
    identity = "cli-fixture@1"

    def translate(self, texts, source_language, target_language, on_log):
        return tuple(f"{target_language}:{text}" for text in texts)


def test_cli_accepts_multiple_languages_and_emits_machine_result(tmp_path, capsys):
    transcript = write_transcript_manifest(tmp_path)

    exit_code = main(
        [
            str(transcript), "--output-dir", str(tmp_path / "out"), "--operation-id", "op-1",
            "--target-language", "ru-RU", "--target-language", "en-US", "--json",
        ],
        adapter_factory=lambda _args: CliAdapter(),
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["resultClass"] == "COMPLETED"
    assert Path(payload["manifest"]).is_file()


def test_public_app_manifest_readme_and_help_are_complete():
    manifest = json.loads((APP / "mvp.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "translation"
    assert manifest["delivery_level"] == "DOMAIN_VERIFIED"
    assert "transcript manifest" in " ".join(manifest["inputs"]).lower()
    assert "translation-manifest.json" in manifest["outputs"]
    assert (APP / manifest["entrypoint"]).is_file()
    assert (APP / manifest["install"]).is_file()
    readme = (APP / "README.md").read_text(encoding="utf-8").lower()
    assert "one work item at a time" in readme
    assert "voice" in readme and "does not" in readme

    completed = subprocess.run(
        [sys.executable, "-m", "translation_app.cli", "--help"],
        cwd=APP,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert completed.returncode == 0
    assert "--target-language" in completed.stdout
    assert "--batch-size" in completed.stdout
