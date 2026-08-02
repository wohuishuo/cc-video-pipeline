import hashlib
import json
from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "publication-batch"
sys.path.insert(0, str(APP))

from publication_batch.cli import main


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assets(tmp_path: Path):
    lineage = []
    for name in ("source", "translation", "voice"):
        path = tmp_path / f"{name}.json"
        path.write_text(name, encoding="utf-8")
        lineage.append(path)
    video = tmp_path / "localized.mp4"
    video.write_bytes(b"video")
    localization = tmp_path / "localization-manifest.json"
    localization.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "sourceManifest": str(lineage[0]),
                "sourceManifestSha256": digest(lineage[0]),
                "translationManifest": str(lineage[1]),
                "translationManifestSha256": digest(lineage[1]),
                "voiceManifest": str(lineage[2]),
                "voiceManifestSha256": digest(lineage[2]),
                "sourceVolume": 0.12,
                "targetLanguages": ["ru-RU"],
                "expectedMediaIds": ["m1"],
                "derivatives": [
                    {
                        "targetLanguage": "ru-RU",
                        "mediaId": "m1",
                        "path": str(video),
                        "sha256": digest(video),
                        "size": video.stat().st_size,
                        "duration": 2.0,
                        "width": 1080,
                        "height": 1920,
                        "videoCodec": "h264",
                        "audioCodec": "aac",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    metadata = tmp_path / "metadata.json"
    metadata.write_text('{"title":"{filename} [{language}]"}', encoding="utf-8")
    return localization, metadata


def test_cli_plans_with_real_publication_child_and_emits_json(tmp_path, capsys):
    localization, metadata = assets(tmp_path)

    code = main(
        [
            "plan",
            str(localization),
            "--metadata-template",
            str(metadata),
            "--target",
            "youtube=primary",
            "--credential",
            "youtube=youtube-main",
            "--output-dir",
            str(tmp_path / "out"),
            "--operation-id",
            "batch-1",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out.splitlines()[-1])

    assert code == 0
    assert payload["resultClass"] == "COMPLETED"
    assert Path(payload["manifest"]).is_file()
    assert payload["manifestSha256"] == digest(Path(payload["manifest"]))
    assert payload["itemCount"] == 1
    assert payload["jobCount"] == 1


def test_cli_rejects_duplicate_target_without_running_child(tmp_path, capsys):
    localization, metadata = assets(tmp_path)

    code = main(
        [
            "plan",
            str(localization),
            "--metadata-template",
            str(metadata),
            "--target",
            "youtube=one",
            "--target",
            "youtube=two",
            "--output-dir",
            str(tmp_path / "out"),
            "--operation-id",
            "batch-1",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["resultClass"] == "REJECTED_MALFORMED"


def test_doctor_reports_strict_serial_publication_owner(capsys):
    assert main(["doctor", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["value"] == {
        "python": sys.version.split()[0],
        "maximumActiveItems": 1,
        "resume": "item-checkpoint",
        "childOwner": "publication",
    }
