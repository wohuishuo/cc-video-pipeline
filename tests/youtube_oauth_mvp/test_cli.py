import json
import os
from pathlib import Path
import subprocess
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "youtube-oauth-bootstrap"


def run_cli(*arguments):
    return subprocess.run([sys.executable, "-m", "youtube_oauth.cli", *arguments], capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PYTHONPATH": str(APP), "PYTHONUTF8": "1"})


def test_doctor_reports_loopback_pkce_and_minimum_scope():
    result = run_cli("doctor", "--json")
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload["value"] == {"python": sys.version.split()[0], "callback": "127.0.0.1:ephemeral", "pkce": "S256", "scope": "youtube.upload"}


def test_missing_client_config_returns_bounded_json_without_starting_consent(tmp_path):
    result = run_cli("connect", "--client-config", str(tmp_path / "missing.json"), "--vault", str(tmp_path / "vault.json"), "--credential-id", "youtube-main", "--label", "Main", "--output-dir", str(tmp_path / "out"), "--operation-id", "op-1", "--no-open", "--json")

    assert result.returncode == 2
    assert json.loads(result.stdout)["resultClass"] == "REJECTED_MALFORMED"
    assert "Traceback" not in result.stderr
