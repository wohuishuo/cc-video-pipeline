import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]; APP=ROOT/"apps"/"creator-discovery"


def test_public_mvp_files_and_help():
    manifest=json.loads((APP/"mvp.json").read_text(encoding="utf-8"))
    assert manifest["name"]=="creator-discovery" and manifest["delivery_level"]=="PLATFORM_INTEGRATED"
    assert (APP/manifest["entrypoint"]).is_file() and (APP/manifest["install"]).is_file()
    result=subprocess.run(["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-File",str(APP/"run.ps1"),"--help"],cwd=ROOT,text=True,capture_output=True,encoding="utf-8")
    assert result.returncode==0 and "profile" in result.stdout and "--max-items" in result.stdout
