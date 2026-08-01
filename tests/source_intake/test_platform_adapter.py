from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "source-intake"
sys.path.insert(0, str(APP))

from intake.contracts import SourceSpec  # noqa: E402
from intake.platform_adapter import PlatformIOTransport  # noqa: E402


def test_adapter_invokes_public_launcher_and_verifies_receipt_and_media(tmp_path):
    launcher = tmp_path / "fake-platform.ps1"
    launcher.write_text(
        """param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Args)
$out = $Args[$Args.IndexOf('--output-dir') + 1]
New-Item -ItemType Directory -Force -Path $out | Out-Null
[IO.File]::WriteAllBytes((Join-Path $out 'clip.mp4'), [byte[]](1,2,3))
'{"platform":"youtube","operation":"download","status":"ok","facts":{"height":1080}}' | Set-Content -Encoding UTF8 (Join-Path $out 'download-receipt.json')
Write-Output 'download complete'
exit 0
""",
        encoding="utf-8-sig",
    )
    logs = []
    result = PlatformIOTransport(launcher).fetch(
        SourceSpec.url("https://youtu.be/abc"), tmp_path / "out", logs.append
    )
    assert result.completed is True
    assert result.media_paths[0].name == "clip.mp4"
    assert result.facts["height"] == 1080
    assert logs == ["download complete"]


def test_adapter_preserves_failed_platform_receipt(tmp_path):
    launcher = tmp_path / "fake-platform.ps1"
    launcher.write_text(
        """param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Args)
$out = $Args[$Args.IndexOf('--output-dir') + 1]
New-Item -ItemType Directory -Force -Path $out | Out-Null
'{"platform":"douyin","operation":"download","status":"failed","facts":{},"error":"blocked"}' | Set-Content -Encoding UTF8 (Join-Path $out 'download-receipt.json')
exit 1
""",
        encoding="utf-8-sig",
    )
    result = PlatformIOTransport(launcher).fetch(
        SourceSpec.url("https://v.douyin.com/abc"), tmp_path / "out", lambda _: None
    )
    assert result.completed is False
    assert result.platform_receipt.is_file()
    assert "blocked" in result.error

