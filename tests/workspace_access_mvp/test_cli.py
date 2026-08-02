import json
import os
from pathlib import Path
import subprocess
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "workspace-access"


def run_cli(*arguments: str, env=None):
    command = [sys.executable, "-m", "workspace_access.cli", *arguments]
    merged = {**os.environ, "PYTHONPATH": str(APP), "PYTHONUTF8": "1", **(env or {})}
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", env=merged)


def test_cli_round_trip_uses_environment_token_and_redacted_decisions(tmp_path):
    registry = tmp_path / "access.json"
    media = tmp_path / "media"
    media.mkdir()
    initialized = run_cli(
        "init", "--registry", str(registry), "--workspace-id", "local",
        "--display-name", "Local Studio", "--allowed-root", str(media), "--json",
    )
    issued = run_cli(
        "issue", "--registry", str(registry), "--workspace-id", "local",
        "--label", "browser", "--scope", "runs:read", "--ttl-hours", "1", "--json",
    )
    token = json.loads(issued.stdout)["value"]["token"]
    authorized = run_cli(
        "authorize", "--registry", str(registry), "--workspace-id", "local",
        "--required-scope", "runs:read", "--token-env", "TEST_ACCESS_TOKEN", "--json",
        env={"TEST_ACCESS_TOKEN": token},
    )
    described = run_cli(
        "describe", "--registry", str(registry), "--workspace-id", "local", "--json"
    )

    assert initialized.returncode == issued.returncode == authorized.returncode == described.returncode == 0
    decision = json.loads(authorized.stdout)
    assert decision["resultClass"] == "AUTHORIZED"
    assert token not in authorized.stdout
    assert token not in authorized.stderr
    assert json.loads(described.stdout)["value"]["allowedRoots"] == [str(media.resolve())]
    assert "credential" not in described.stdout.lower()


def test_cli_missing_token_is_a_bounded_denial(tmp_path):
    result = run_cli(
        "authorize", "--registry", str(tmp_path / "missing.json"),
        "--workspace-id", "local", "--required-scope", "runs:read",
        "--token-env", "DEFINITELY_MISSING_TOKEN", "--json",
    )
    assert result.returncode == 3
    assert json.loads(result.stdout)["resultClass"] == "REJECTED_UNAUTHORIZED"
