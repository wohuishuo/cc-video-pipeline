from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "apps" / "localization"
sys.path.insert(0, str(APP))

from localizer.edge_video_localizer import retry_delays, run_serial_jobs  # noqa: E402


def test_serial_jobs_finishes_each_video_before_starting_next():
    events = []

    def process(job_id):
        events.extend([(job_id, "tts"), (job_id, "mix"), (job_id, "render")])

    assert run_serial_jobs(["111", "222"], process) == []
    assert events == [
        ("111", "tts"), ("111", "mix"), ("111", "render"),
        ("222", "tts"), ("222", "mix"), ("222", "render"),
    ]


def test_serial_jobs_records_failure_and_continues():
    visited = []

    def process(job_id):
        visited.append(job_id)
        if job_id == "111":
            raise RuntimeError("network unavailable")

    failures = run_serial_jobs(["111", "222"], process)
    assert visited == ["111", "222"]
    assert failures == [{"job_id": "111", "error": "network unavailable"}]


def test_retry_delays_back_off_without_growing_forever():
    assert retry_delays(6, initial_seconds=5, maximum_seconds=60) == [5, 10, 20, 40, 60]


def test_edge_cli_exposes_serial_contract():
    completed = subprocess.run(
        [sys.executable, "-m", "localizer.edge_video_localizer", "--help"],
        cwd=APP,
        env={**__import__("os").environ, "PYTHONPATH": str(APP)},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert completed.returncode == 0
    assert "--batch-manifest" in completed.stdout
    assert "--voice" in completed.stdout
    assert "--output-root" in completed.stdout
    assert "--job-id" in completed.stdout


def test_powershell_launcher_exists():
    assert (APP / "edge-russian.ps1").is_file()
