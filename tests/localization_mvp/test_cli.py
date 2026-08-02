import json
from pathlib import Path
import subprocess
import sys

APP=Path(__file__).resolve().parents[2]/"apps"/"localization"
sys.path.insert(0,str(APP))

from .helpers import manifests  # noqa: E402
from localization_app.cli import main  # noqa: E402
from localization_app.ffmpeg import ProbeResult  # noqa: E402


class CliAdapter:
    identity="cli-composer@1"
    def compose(self,job,output,on_log,*,source_volume):
        output.parent.mkdir(parents=True,exist_ok=True); output.write_bytes(b"mp4")
        return ProbeResult(4.0,320,240,"h264","aac",True)


def test_cli_accepts_three_explicit_manifests_and_emits_result(tmp_path,capsys):
    source,translation,voice=manifests(tmp_path)
    code=main([str(source),str(translation),str(voice),"--output-dir",str(tmp_path/"out"),"--operation-id","op-1","--json"],adapter_factory=lambda _args:CliAdapter())
    assert code==0
    payload=json.loads(capsys.readouterr().out)
    assert payload["resultClass"]=="COMPLETED" and Path(payload["manifest"]).is_file()


def test_public_launcher_manifest_readme_and_help_match_new_boundary():
    manifest=json.loads((APP/"mvp.json").read_text(encoding="utf-8"))
    assert manifest["name"]=="localization" and manifest["delivery_level"]=="DOMAIN_VERIFIED"
    assert "Source Manifest" in manifest["inputs"] and "Voice Manifest" in manifest["inputs"]
    assert (APP/manifest["entrypoint"]).is_file() and (APP/manifest["install"]).is_file()
    readme=(APP/"README.md").read_text(encoding="utf-8")
    assert "does not translate" in readme and "source audio" in readme
    completed=subprocess.run([sys.executable,"-m","localization_app.cli","--help"],cwd=APP,capture_output=True,text=True)
    assert completed.returncode==0 and "source_manifest" in completed.stdout and "voice_manifest" in completed.stdout
