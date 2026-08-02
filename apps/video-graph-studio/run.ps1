param(
    [int]$Port = 8765,
    [string]$DataRoot = (Join-Path $env:LOCALAPPDATA "VideoGraphStudio"),
    [string]$AccessRegistry,
    [string]$WorkspaceId,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$appRoot = $PSScriptRoot
$repository = (Resolve-Path (Join-Path $appRoot "..\..")).Path
$gitCommon = (& git -C $repository rev-parse --git-common-dir).Trim()
if ([IO.Path]::IsPathRooted($gitCommon)) {
    $commonPath = (Resolve-Path $gitCommon).Path
} else {
    $commonPath = (Resolve-Path (Join-Path $repository $gitCommon)).Path
}
$mainRoot = Split-Path -Parent $commonPath
$python = Join-Path $mainRoot "tools\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $python = Join-Path $repository "tools\.venv\Scripts\python.exe"
}
if (-not (Test-Path -LiteralPath $python)) {
    throw "Python 3.12 runtime not found. Run apps/video-graph-studio/install.ps1 first."
}

$env:PYTHONPATH = $appRoot
$env:PYTHONUTF8 = "1"
$arguments = @("-m", "studio.server", "--port", $Port, "--data-root", $DataRoot)
if ($NoBrowser) { $arguments += "--no-browser" }
if ([bool]$AccessRegistry -ne [bool]$WorkspaceId) { throw "AccessRegistry and WorkspaceId must be provided together." }
if ($AccessRegistry) { $arguments += @("--access-registry", $AccessRegistry, "--workspace-id", $WorkspaceId) }
& $python @arguments
exit $LASTEXITCODE
