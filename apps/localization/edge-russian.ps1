param(
    [Parameter(Mandatory = $true)]
    [string]$SourceRoot,
    [string]$Voice = "ru-RU-DmitryNeural"
)

$ErrorActionPreference = "Stop"
$appRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$gitCommon = (& git -C $appRoot rev-parse --git-common-dir).Trim()
$runtimeRoot = (Resolve-Path (Join-Path $gitCommon "..")).Path
$python = Join-Path $runtimeRoot "tools\.venv\Scripts\python.exe"
$russianRoot = Join-Path $SourceRoot "russian"
$manifest = Join-Path $russianRoot "batch-manifest.json"
$output = Join-Path $russianRoot "edge-final"
$env:PYTHONPATH = $appRoot
$env:PYTHONUTF8 = "1"

& $python -m localizer.edge_video_localizer `
    --batch-manifest $manifest `
    --output-root $output `
    --voice $Voice
exit $LASTEXITCODE
