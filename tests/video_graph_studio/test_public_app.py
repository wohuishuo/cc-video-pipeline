import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "apps" / "video-graph-studio"
sys.path.insert(0, str(ROOT))

from scripts.validate_mvp_manifests import validate_repository  # noqa: E402


def test_public_application_manifest_and_paths_are_complete():
    manifest = json.loads((APP / "mvp.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "video-graph-studio"
    assert manifest["delivery_level"] in {"IMPLEMENTED", "DOMAIN_VERIFIED"}
    assert (APP / manifest["entrypoint"]).is_file()
    assert (APP / manifest["install"]).is_file()
    assert validate_repository(ROOT) == []


def test_public_readme_documents_lifecycle_and_data_ownership():
    readme = (APP / "README.md").read_text(encoding="utf-8").lower()
    assert "start" in readme
    assert "stop" in readme
    assert "data root" in readme
    assert "127.0.0.1" in readme
    assert "one workflow" in readme


def test_server_cli_exposes_port_data_and_browser_controls():
    completed = subprocess.run(
        [sys.executable, "-m", "studio.server", "--help"],
        cwd=APP,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert completed.returncode == 0
    assert "--port" in completed.stdout
    assert "--data-root" in completed.stdout
    assert "--no-browser" in completed.stdout

