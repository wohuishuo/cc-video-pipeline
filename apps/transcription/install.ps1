$ErrorActionPreference = "Stop"
$repository = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$gitCommon = (& git -C $repository rev-parse --git-common-dir).Trim()
$commonPath = if ([IO.Path]::IsPathRooted($gitCommon)) { (Resolve-Path $gitCommon).Path } else { (Resolve-Path (Join-Path $repository $gitCommon)).Path }
$mainRoot = Split-Path -Parent $commonPath
$venv = Join-Path $mainRoot "tools\.venv"
if (-not (Test-Path -LiteralPath (Join-Path $venv "Scripts\python.exe"))) { python -m venv $venv }
$python = Join-Path $venv "Scripts\python.exe"
& $python -m pip install faster-whisper
& ffmpeg -version | Select-Object -First 1
Write-Host "Transcription is ready." -ForegroundColor Green
