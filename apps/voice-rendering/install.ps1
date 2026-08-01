$ErrorActionPreference = "Stop"
$repository = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$gitCommon = (& git -C $repository rev-parse --git-common-dir).Trim()
$commonPath = if ([IO.Path]::IsPathRooted($gitCommon)) { (Resolve-Path $gitCommon).Path } else { (Resolve-Path (Join-Path $repository $gitCommon)).Path }
$venv = Join-Path (Split-Path -Parent $commonPath) "tools\.venv"
if (-not (Test-Path -LiteralPath (Join-Path $venv "Scripts\python.exe"))) { python -m venv $venv }
& (Join-Path $venv "Scripts\python.exe") -m pip install edge-tts
& ffmpeg -version | Select-Object -First 1
Write-Host "Voice Rendering is ready." -ForegroundColor Green
