import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]; APP=ROOT/"apps"/"publication"


def test_public_files_and_help():
    manifest=json.loads((APP/"mvp.json").read_text(encoding="utf-8"))
    assert manifest["name"]=="publication" and manifest["delivery_level"]=="DOMAIN_VERIFIED"
    result=subprocess.run(["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-File",str(APP/"run.ps1"),"--help"],cwd=ROOT,text=True,capture_output=True,encoding="utf-8")
    assert result.returncode==0 and "plan" in result.stdout and "execute" in result.stdout
