import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "apps" / "creator-selection"


def _manifest(tmp_path: Path) -> Path:
    path = tmp_path / "creator.json"
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "platform": "youtube",
                "creator": {"id": "c", "name": "Creator"},
                "items": [
                    {"ordinal": 1, "id": "a", "url": "https://youtube.com/watch?v=a", "title": "A", "publishedAt": None},
                    {"ordinal": 2, "id": "b", "url": "https://youtube.com/watch?v=b", "title": "B", "publishedAt": None},
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_public_launcher_selects_exact_ids_from_any_working_directory(tmp_path):
    source = _manifest(tmp_path)
    completed = subprocess.run(
        [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(APP / "run.ps1"),
            "select", str(source), "--video-id", "b", "--output-dir", str(tmp_path / "out"),
            "--operation-id", "public-op", "--json",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=30,
    )
    payload = json.loads(completed.stdout.strip().splitlines()[-1])

    assert completed.returncode == 0, completed.stderr
    assert payload["resultClass"] == "COMPLETED"
    assert Path(payload["manifest"]).is_file()


def test_mvp_manifest_declares_independent_public_program():
    value = json.loads((APP / "mvp.json").read_text(encoding="utf-8"))
    assert value["name"] == "creator-selection"
    assert value["delivery_level"] == "DOMAIN_VERIFIED"
    assert (APP / value["entrypoint"]).is_file()
    assert "creator-selection-manifest.json" in value["outputs"]
