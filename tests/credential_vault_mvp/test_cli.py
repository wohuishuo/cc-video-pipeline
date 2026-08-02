import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "credential-vault"


def run_cli(*arguments: str, extra_env: dict[str, str] | None = None):
    command = [sys.executable, "-m", "credential_vault.cli", *arguments]
    environment = {
        **os.environ,
        "PYTHONPATH": str(APP),
        "PYTHONUTF8": "1",
        **(extra_env or {}),
    }
    return subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", env=environment
    )


def test_cli_accepts_secret_from_environment_and_never_echoes_it(tmp_path):
    vault = tmp_path / "vault.json"
    secret = "not-for-stdout-or-disk"

    result = run_cli(
        "put",
        "--vault",
        str(vault),
        "--credential-id",
        "youtube-main",
        "--provider",
        "youtube",
        "--label",
        "Main channel",
        "--secret-env",
        "TEST_SECRET",
        "--json",
        extra_env={"TEST_SECRET": secret},
    )
    described = run_cli(
        "describe",
        "--vault",
        str(vault),
        "--credential-id",
        "youtube-main",
        "--json",
    )

    assert result.returncode == described.returncode == 0
    assert json.loads(result.stdout)["resultClass"] == "COMPLETED"
    assert json.loads(described.stdout)["value"]["status"] == "ACTIVE"
    assert secret not in result.stdout + result.stderr + described.stdout + described.stderr
    assert secret not in vault.read_text(encoding="utf-8")
    assert "ciphertext" not in described.stdout


def test_cli_rejects_missing_secret_environment_variable(tmp_path):
    result = run_cli(
        "put",
        "--vault",
        str(tmp_path / "vault.json"),
        "--credential-id",
        "youtube-main",
        "--provider",
        "youtube",
        "--label",
        "Main",
        "--secret-env",
        "INTENTIONALLY_MISSING_SECRET",
        "--json",
    )

    assert result.returncode == 2
    assert json.loads(result.stdout)["resultClass"] == "REJECTED_SECRET"


def test_cli_run_injects_secret_only_into_child_environment(tmp_path):
    vault = tmp_path / "vault.json"
    secret = "child-only-secret"
    put = run_cli(
        "put", "--vault", str(vault), "--credential-id", "youtube-main",
        "--provider", "youtube", "--label", "Main", "--secret-env", "TEST_SECRET",
        "--json", extra_env={"TEST_SECRET": secret},
    )
    assert put.returncode == 0
    expected_hash = hashlib.sha256(secret.encode("utf-8")).hexdigest()
    child = (
        "import hashlib,os,sys; value=os.environ.get('PLATFORM_SECRET',''); "
        f"sys.exit(0 if hashlib.sha256(value.encode()).hexdigest() == '{expected_hash}' "
        "else 9)"
    )

    result = run_cli(
        "run", "--vault", str(vault), "--credential-id", "youtube-main",
        "--target-env", "PLATFORM_SECRET", "--executable", sys.executable,
        "--argument=-c", "--argument", child,
    )

    assert result.returncode == 0
    assert secret not in result.stdout + result.stderr


def test_cli_run_propagates_child_exit_code(tmp_path):
    vault = tmp_path / "vault.json"
    put = run_cli(
        "put", "--vault", str(vault), "--credential-id", "youtube-main",
        "--provider", "youtube", "--label", "Main", "--secret-env", "TEST_SECRET",
        "--json", extra_env={"TEST_SECRET": "secret"},
    )
    assert put.returncode == 0

    result = run_cli(
        "run", "--vault", str(vault), "--credential-id", "youtube-main",
        "--target-env", "PLATFORM_SECRET", "--executable", sys.executable,
        "--argument=-c", "--argument", "raise SystemExit(7)",
    )

    assert result.returncode == 7


def test_cli_run_returns_bounded_error_when_executable_is_missing(tmp_path):
    vault = tmp_path / "vault.json"
    secret = "must-not-leak-on-launch-failure"
    put = run_cli(
        "put", "--vault", str(vault), "--credential-id", "youtube-main",
        "--provider", "youtube", "--label", "Main", "--secret-env", "TEST_SECRET",
        "--json", extra_env={"TEST_SECRET": secret},
    )
    assert put.returncode == 0

    result = run_cli(
        "run", "--vault", str(vault), "--credential-id", "youtube-main",
        "--target-env", "PLATFORM_SECRET", "--executable", str(tmp_path / "missing.exe"),
        "--json",
    )

    assert result.returncode == 2
    assert json.loads(result.stdout)["resultClass"] == "REJECTED_CHILD"
    assert "Traceback" not in result.stderr
    assert secret not in result.stdout + result.stderr
