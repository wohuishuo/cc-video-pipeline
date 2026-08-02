import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "apps" / "publication-batch-execution"
sys.path.insert(0, str(APP))

from publication_batch_execution.cli import main


def test_public_files_help_and_doctor_report_independent_owner(capsys):
    manifest = json.loads((APP / "mvp.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "publication-batch-execution"
    assert manifest["delivery_level"] == "DOMAIN_VERIFIED"
    help_result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(APP / "run.ps1"), "--help"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert help_result.returncode == 0 and "execute" in help_result.stdout and "doctor" in help_result.stdout

    assert main(["doctor", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "resultClass": "COMPLETED",
        "value": {
            "python": sys.version.split()[0], "maximumActiveItems": 1,
            "resume": "item-checkpoint", "childOwner": "publication",
            "platformPolicy": "credential-backed-private-youtube",
        },
    }


def test_cli_rejects_wrong_confirmation_without_starting_executor(capsys, tmp_path):
    plan = tmp_path / "batch.json"; plan.write_text("{}", encoding="utf-8")
    vault = tmp_path / "vault.json"; vault.write_text("{}", encoding="utf-8")
    called = []

    code = main(
        [
            "execute", str(plan), "--confirmation", "0" * 64,
            "--credential-vault", str(vault), "--output-dir", str(tmp_path / "out"),
            "--operation-id", "cli-op", "--json",
        ],
        executor_factory=lambda repository, args: called.append(repository),
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["resultClass"] == "REJECTED_CONFIRMATION"
    assert called == []
