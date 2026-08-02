from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]


def test_browser_workflow_model_contracts():
    completed = subprocess.run(
        ["node", "--test", "tests/video_graph_studio/workflow_model.test.mjs"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
