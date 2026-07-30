[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$SourceRoot,
    [switch]$SkipSeparation,
    [switch]$SkipRender
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$codeRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$runtimeRoot = $codeRoot
$common = (& git -C $codeRoot rev-parse --git-common-dir).Trim()
if (-not [string]::IsNullOrWhiteSpace($common)) {
    if (-not [IO.Path]::IsPathRooted($common)) { $common = Join-Path $codeRoot $common }
    $candidateRuntimeRoot = Split-Path (Resolve-Path $common).Path -Parent
    if (Test-Path -LiteralPath (Join-Path $candidateRuntimeRoot "tools\qwen3tts-env\Scripts\python.exe")) {
        $runtimeRoot = $candidateRuntimeRoot
    }
}
$python = Join-Path $runtimeRoot "tools\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) { throw "Missing orchestration Python: $python" }

$env:PYTHONPATH = Join-Path $codeRoot "apps\localization"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$arguments = @(
    "-m", "localizer.batch",
    "--source-root", (Resolve-Path $SourceRoot).Path,
    "--runtime-root", $runtimeRoot
)
if ($SkipSeparation) { $arguments += "--skip-separation" }
if ($SkipRender) { $arguments += "--skip-render" }
& $python @arguments
exit $LASTEXITCODE
