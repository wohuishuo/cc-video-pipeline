import json
from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "creator-batch"
sys.path.insert(0, str(APP))

from creator_batch.cli import main
from creator_batch.operation import ItemProcessResult


def creator_manifest(tmp_path):
    path = tmp_path / "creator-manifest.json"
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "platform": "douyin",
                "creator": {"id": "creator", "name": "Creator"},
                "items": [
                    {"ordinal": 1, "id": "video-1", "url": "https://www.douyin.com/video/1", "title": "First", "publishedAt": None}
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


class Processor:
    def process(self, item, item_root, child_prefix, batch_policy, cookies, on_log):
        manifest = Path(item_root) / "localization-manifest.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text('{"schemaVersion":1,"derivatives":[{"path":"video.mp4"}]}', encoding="utf-8")
        return ItemProcessResult(True, manifest, 1)


def test_cli_runs_injected_processor_and_emits_committed_json(tmp_path, capsys):
    output = tmp_path / "out"

    code = main(
        [
            "localize",
            str(creator_manifest(tmp_path)),
            "--target-language",
            "ru-RU",
            "--voice",
            "ru-RU=ru-RU-DmitryNeural",
            "--output-dir",
            str(output),
            "--operation-id",
            "batch-1",
            "--json",
        ],
        processor_factory=lambda _repository, _args: Processor(),
    )
    payload = json.loads(capsys.readouterr().out.splitlines()[-1])

    assert code == 0
    assert payload["resultClass"] == "COMPLETED"
    assert Path(payload["manifest"]).is_file()
    assert Path(payload["receipt"]).is_file()


def test_cli_rejects_duplicate_language_and_mismatched_voice_policy(tmp_path, capsys):
    code = main(
        [
            "localize",
            str(creator_manifest(tmp_path)),
            "--target-language",
            "ru-RU",
            "--target-language",
            "ru-RU",
            "--voice",
            "en-US=en-US-GuyNeural",
            "--output-dir",
            str(tmp_path / "out"),
            "--operation-id",
            "batch-1",
            "--json",
        ],
        processor_factory=lambda _repository, _args: Processor(),
    )
    payload = json.loads(capsys.readouterr().out.splitlines()[-1])

    assert code == 2
    assert payload["resultClass"] == "REJECTED_MALFORMED"


def test_cli_rejects_missing_cookie_without_echoing_its_path(tmp_path, capsys):
    missing = tmp_path / "private-cookies.txt"
    code = main(
        [
            "localize",
            str(creator_manifest(tmp_path)),
            "--target-language",
            "ru-RU",
            "--voice",
            "ru-RU=voice",
            "--cookies",
            str(missing),
            "--output-dir",
            str(tmp_path / "out"),
            "--operation-id",
            "batch-1",
            "--json",
        ],
        processor_factory=lambda _repository, _args: Processor(),
    )
    rendered = capsys.readouterr().out

    assert code == 2
    assert json.loads(rendered)["resultClass"] == "REJECTED_MALFORMED"
    assert "private-cookies" not in rendered


def test_doctor_reports_strict_serial_policy(capsys):
    assert main(["doctor", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["value"]["maximumActiveItems"] == 1
