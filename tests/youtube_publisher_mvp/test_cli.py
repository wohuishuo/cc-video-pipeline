import json
import os
from pathlib import Path
import subprocess
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "youtube-publisher"


def run_cli(*arguments, extra_env=None):
    environment = {**os.environ, "PYTHONPATH": str(APP), "PYTHONUTF8": "1", **(extra_env or {})}
    return subprocess.run([sys.executable, "-m", "youtube_publisher.cli", *arguments], capture_output=True, text=True, encoding="utf-8", env=environment)


def test_doctor_describes_private_resumable_boundary():
    result = run_cli("doctor", "--json")

    assert result.returncode == 0
    assert json.loads(result.stdout)["value"]["visibility"] == "private-only"


def test_cli_rejects_missing_credential_without_traceback(tmp_path):
    video = tmp_path / "video.mp4"; video.write_bytes(b"video")
    metadata = tmp_path / "metadata.json"; metadata.write_text('{"title":"Demo"}', encoding="utf-8")

    result = run_cli("upload", str(video), "--metadata", str(metadata), "--credential-env", "MISSING_YOUTUBE_CREDENTIAL", "--output-dir", str(tmp_path / "out"), "--operation-id", "op-1", "--json")

    assert result.returncode == 2
    assert json.loads(result.stdout)["resultClass"] == "REJECTED_SECRET"
    assert "Traceback" not in result.stderr
