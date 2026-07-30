[CmdletBinding()]
param(
    [string]$SeparatorModelDir,
    [string]$RuntimeRoot,
    [switch]$VerifyModelOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = if ([string]::IsNullOrWhiteSpace($RuntimeRoot)) {
    (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
} else {
    (Resolve-Path $RuntimeRoot).Path
}
$tools = Join-Path $root "tools"
$orchestrationVenv = Join-Path $tools ".venv"
$separatorVenv = Join-Path $tools "audio-separator-env"
$modelFilename = "MDX23C-8KFFT-InstVoc_HQ.ckpt"
# Derived 2026-07-30 from the exact TRvlvr/model_repo release asset used by
# audio-separator 0.44.5 (448,101,203 bytes):
# https://github.com/TRvlvr/model_repo/releases/download/all_public_uvr_models/MDX23C-8KFFT-InstVoc_HQ.ckpt
$modelSha256 = "49d51472769e34a2501cd1da782346a3212555c3a5619fc2c53507445528d816"
if ([string]::IsNullOrWhiteSpace($SeparatorModelDir)) {
    $SeparatorModelDir = Join-Path $tools "audio-separator-models"
}
$modelPath = Join-Path $SeparatorModelDir $modelFilename

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$CommandArguments
    )
    & $Command @CommandArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $Command $($CommandArguments -join ' ')"
    }
}

function Ensure-Venv {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$PythonVersion
    )
    $python = Join-Path $Path "Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        $launcher = Get-Command "py.exe" -ErrorAction SilentlyContinue
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Path) | Out-Null
        if ($null -ne $launcher) {
            & $launcher.Source "-$PythonVersion" "-m" "venv" $Path
        }
        if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
            $qwenPython = Join-Path $root "tools\qwen3tts-env\Scripts\python.exe"
            if ($PythonVersion -eq "3.11" -and (Test-Path -LiteralPath $qwenPython -PathType Leaf)) {
                & $qwenPython -m venv $Path
            }
        }
    }
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw "Virtual environment creation did not produce $python"
    }
    $actualVersion = (& $python "-c" "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "Cannot inspect Python in $Path"
    }
    if ($actualVersion -ne $PythonVersion) {
        throw "$Path uses Python $actualVersion; Python $PythonVersion is required"
    }
    return $python
}

function Assert-OfficialSeparatorModel {
    param(
        [Parameter(Mandatory = $true)][string]$Path
    )
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing separator model: $Path"
    }
    $actualSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
    if ($actualSha256 -ne $modelSha256) {
        throw "Separator model SHA-256 mismatch for $Path. Expected $modelSha256, got $actualSha256"
    }
}

if ($VerifyModelOnly) {
    Assert-OfficialSeparatorModel $modelPath
    Write-Host "Verified separator model SHA-256: $modelSha256"
    exit 0
}

$orchestrationPython = Ensure-Venv $orchestrationVenv "3.12"
Invoke-Checked $orchestrationPython "-m" "pip" "install" "--disable-pip-version-check" "edge-tts" "faster-whisper"

$separatorPython = Ensure-Venv $separatorVenv "3.11"
Invoke-Checked $separatorPython "-m" "pip" "install" "--disable-pip-version-check" "audio-separator[gpu]==0.44.5"

$separatorCli = Join-Path $separatorVenv "Scripts\audio-separator.exe"
if (-not (Test-Path -LiteralPath $separatorCli -PathType Leaf)) {
    throw "audio-separator installation did not produce $separatorCli"
}

$priorErrorPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$envInfo = (& $separatorCli "--env_info" 2>&1 | Out-String)
$envInfoExitCode = $LASTEXITCODE
$ErrorActionPreference = $priorErrorPreference
if ($envInfoExitCode -ne 0) {
    throw "audio-separator --env_info failed with exit code $envInfoExitCode`n$envInfo"
}
if ($envInfo -notmatch "(?i)ONNXruntime has CUDAExecutionProvider available") {
    throw "audio-separator GPU validation failed: CUDA and CUDAExecutionProvider are required.`n$envInfo"
}
if ($envInfo -notmatch "(?i)FFmpeg installed") {
    throw "audio-separator runtime validation failed: FFmpeg is required.`n$envInfo"
}

New-Item -ItemType Directory -Force -Path $SeparatorModelDir | Out-Null
if (Test-Path -LiteralPath $modelPath -PathType Leaf) {
    $installedSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $modelPath).Hash.ToLowerInvariant()
    if ($installedSha256 -ne $modelSha256) {
        Write-Warning "Removing separator model with untrusted SHA-256: $installedSha256"
        Remove-Item -LiteralPath $modelPath -Force
    }
}
if (-not (Test-Path -LiteralPath $modelPath -PathType Leaf)) {
    Invoke-Checked $separatorCli `
        "--model_filename" $modelFilename `
        "--model_file_dir" $SeparatorModelDir `
        "--download_model_only"
}
Assert-OfficialSeparatorModel $modelPath

Write-Host "Localization runtimes are ready."
Write-Host "Orchestration Python: $orchestrationPython"
Write-Host "Separator Python: $separatorPython"
Write-Host "Separator model: $modelPath"
