$ErrorActionPreference = "Stop"
$repository = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$gitCommon = (& git -C $repository rev-parse --git-common-dir).Trim()
$commonPath = if ([IO.Path]::IsPathRooted($gitCommon)) { (Resolve-Path $gitCommon).Path } else { (Resolve-Path (Join-Path $repository $gitCommon)).Path }
$venv = Join-Path (Split-Path -Parent $commonPath) "tools\.venv"
if (-not (Test-Path -LiteralPath (Join-Path $venv "Scripts\python.exe"))) { python -m venv $venv }
& ffmpeg -version | Select-Object -First 1
& ffprobe -version | Select-Object -First 1
Write-Host "Localization composition is ready." -ForegroundColor Green
