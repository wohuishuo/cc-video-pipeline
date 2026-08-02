from pathlib import Path
import subprocess


ROOT=Path(__file__).resolve().parents[2]


def test_pinned_f2_helper_compatibility_imports():
    python=ROOT.parents[1]/".tools"/"f2"/".venv"/"Scripts"/"python.exe"
    if not python.is_file(): return
    helper=ROOT/"apps"/"creator-discovery"/"creator_discovery"/"f2_helper.py"
    result=subprocess.run([str(python),str(helper),"--doctor"],text=True,capture_output=True,encoding="utf-8",errors="replace")
    assert result.returncode==0 and json_ready(result.stdout)


def json_ready(value):
    return '"ready": true' in value.lower()
