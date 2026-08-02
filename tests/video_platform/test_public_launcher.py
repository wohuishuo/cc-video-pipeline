from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]


def test_public_launcher_loads_video_platform_from_any_working_directory(tmp_path):
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "video-platform.ps1"),
            "--help",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "download" in completed.stdout
    assert "upload" in completed.stdout
