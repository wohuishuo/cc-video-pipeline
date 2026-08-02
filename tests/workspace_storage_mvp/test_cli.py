import json
import os
from pathlib import Path
import subprocess
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "workspace-storage"


def run_cli(*arguments: str):
    command = [sys.executable, "-m", "workspace_storage.cli", *arguments]
    environment = {**os.environ, "PYTHONPATH": str(APP), "PYTHONUTF8": "1"}
    return subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", env=environment
    )


def test_cli_provision_resolve_capacity_and_describe(tmp_path):
    registry = tmp_path / "storage.json"
    storage_root = tmp_path / "runtime"
    common = ("--registry", str(registry), "--workspace-id", "alpha", "--json")

    provisioned = run_cli(
        "provision", *common, "--storage-root", str(storage_root), "--quota-bytes", "100"
    )
    resolved = run_cli(
        "resolve", *common, "--kind", "artifacts", "--relative-path", "runs/one.mp4"
    )
    capacity = run_cli("capacity", *common, "--required-bytes", "100")
    quota_denied = run_cli("capacity", *common, "--required-bytes", "101")
    described = run_cli("describe", *common)

    assert provisioned.returncode == resolved.returncode == capacity.returncode == described.returncode == 0
    assert json.loads(provisioned.stdout)["resultClass"] == "COMPLETED"
    assert json.loads(resolved.stdout)["value"]["path"].endswith("one.mp4")
    assert json.loads(capacity.stdout)["resultClass"] == "ALLOWED"
    assert quota_denied.returncode == 3
    assert json.loads(quota_denied.stdout)["resultClass"] == "REJECTED_QUOTA"
    assert json.loads(described.stdout)["value"]["quotaBytes"] == 100


def test_cli_rejects_path_escape_with_bounded_result(tmp_path):
    registry = tmp_path / "storage.json"
    storage_root = tmp_path / "runtime"
    common = ("--registry", str(registry), "--workspace-id", "alpha", "--json")
    run_cli("provision", *common, "--storage-root", str(storage_root), "--quota-bytes", "100")

    escaped = run_cli(
        "resolve", *common, "--kind", "artifacts", "--relative-path", "../escape"
    )

    assert escaped.returncode == 2
    assert json.loads(escaped.stdout)["resultClass"] == "REJECTED_PATH"
