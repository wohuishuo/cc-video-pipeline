from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "apps" / "localization"


def test_batch_cli_exposes_one_command_contract():
    completed = subprocess.run(
        [sys.executable, "-m", "localizer.batch", "--help"],
        cwd=APP,
        env={**__import__("os").environ, "PYTHONPATH": str(APP)},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert completed.returncode == 0
    assert "--source-root" in completed.stdout
    assert "--runtime-root" in completed.stdout
    assert "--skip-separation" in completed.stdout
    assert "--skip-render" in completed.stdout


def test_public_powershell_launcher_exists():
    launcher = APP / "batch-russian.ps1"
    assert launcher.is_file()
