$ErrorActionPreference = "Stop"
$repository = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$gitCommon = (& git -C $repository rev-parse --git-common-dir).Trim()
$commonPath = if ([IO.Path]::IsPathRooted($gitCommon)) {
    (Resolve-Path $gitCommon).Path
} else {
    (Resolve-Path (Join-Path $repository $gitCommon)).Path
}
$mainRoot = Split-Path -Parent $commonPath
$python = Join-Path $mainRoot "tools\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Repository Python 3.12 runtime is missing: $python"
}
& $python -c "import sqlite3; print('Python and SQLite ready')"
& ffmpeg -version | Select-Object -First 1
& $python -c "import edge_tts; print('Edge-TTS ready')"
Write-Host "Video Graph Studio is ready." -ForegroundColor Green

