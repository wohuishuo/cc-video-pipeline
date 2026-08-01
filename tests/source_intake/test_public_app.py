import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "apps" / "source-intake"


def test_source_intake_public_application_contract():
    manifest = json.loads((APP / "mvp.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "source-intake"
    assert manifest["delivery_level"] == "DOMAIN_VERIFIED"
    assert (APP / manifest["entrypoint"]).is_file()
    assert (APP / manifest["install"]).is_file()
    readme = (APP / "README.md").read_text(encoding="utf-8")
    assert "folder" in readme.lower() and "url" in readme.lower()
    assert "cookies are optional" in readme.lower()


def test_source_intake_cli_has_folder_and_url_modes():
    completed = subprocess.run(
        [sys.executable, "-m", "intake.cli", "--help"],
        cwd=APP,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert completed.returncode == 0
    assert "folder" in completed.stdout
    assert "url" in completed.stdout

