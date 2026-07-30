from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "apps" / "localization"
sys.path.insert(0, str(APP))

from localizer.batch import _run_job_sequence  # noqa: E402


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


def test_job_sequence_finishes_each_video_before_starting_next():
    events = []

    def localize(job_id):
        events.extend([(job_id, "voice"), (job_id, "mix"), (job_id, "render")])

    assert _run_job_sequence(["111", "222"], localize) == []
    assert events == [
        ("111", "voice"), ("111", "mix"), ("111", "render"),
        ("222", "voice"), ("222", "mix"), ("222", "render"),
    ]


def test_job_sequence_records_failure_and_continues():
    visited = []

    def localize(job_id):
        visited.append(job_id)
        if job_id == "111":
            raise RuntimeError("CUDA out of memory")

    failures = _run_job_sequence(["111", "222"], localize)
    assert visited == ["111", "222"]
    assert failures == [{"job_id": "111", "error": "CUDA out of memory"}]
