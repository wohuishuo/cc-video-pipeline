param(
    [int]$Port = 8765,
    [string]$DataRoot = (Join-Path $env:LOCALAPPDATA "VideoGraphStudio"),
    [string]$AccessRegistry,
    [string]$StorageRegistry,
    [string]$WorkspaceId,
    [string]$ResourceBudgetDatabase,
    [long]$ResourceReservationBytes = 0,
    [int]$ResourceLeaseTtlSeconds = 30,
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

$arguments = @("-m", "studio.server", "--port", $Port, "--data-root", $DataRoot)
if ($NoBrowser) { $arguments += "--no-browser" }
if ([bool]$ResourceBudgetDatabase -ne ($ResourceReservationBytes -gt 0)) {
    throw "ResourceBudgetDatabase and a positive ResourceReservationBytes must be provided together."
}
if ($ResourceBudgetDatabase) {
    $arguments += @(
        "--resource-budget-database", $ResourceBudgetDatabase,
        "--resource-reservation-bytes", $ResourceReservationBytes,
        "--resource-lease-ttl-seconds", $ResourceLeaseTtlSeconds
    )
}
if ($StorageRegistry) {
    if (-not $AccessRegistry -or $WorkspaceId) { throw "Multi-workspace mode requires AccessRegistry and StorageRegistry without WorkspaceId." }
    $arguments += @("--access-registry", $AccessRegistry, "--storage-registry", $StorageRegistry)
} else {
    if ([bool]$AccessRegistry -ne [bool]$WorkspaceId) { throw "AccessRegistry and WorkspaceId must be provided together." }
    if ($AccessRegistry) { $arguments += @("--access-registry", $AccessRegistry, "--workspace-id", $WorkspaceId) }
}

$previousPythonPath = $env:PYTHONPATH
$previousPythonUtf8 = $env:PYTHONUTF8
$exitCode = 1
Push-Location -LiteralPath $appRoot
try {
    $env:PYTHONPATH = $appRoot
    $env:PYTHONUTF8 = "1"
    & $python @arguments
    $exitCode = $LASTEXITCODE
} finally {
    Pop-Location
    $env:PYTHONPATH = $previousPythonPath
    $env:PYTHONUTF8 = $previousPythonUtf8
}
exit $exitCode
