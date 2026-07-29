param([switch]$SkipPythonDependencies)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$lock = Get-Content (Join-Path $root "vendor\video-uploaders.lock.json") -Raw | ConvertFrom-Json
$dep = $lock.dependencies.'social-auto-upload'
$checkout = Join-Path $root $dep.checkout

if (-not (Test-Path (Join-Path $checkout ".git"))) {
  New-Item -ItemType Directory -Force (Split-Path -Parent $checkout) | Out-Null
  git clone --filter=blob:none $dep.url $checkout
}
git -C $checkout fetch --depth 1 origin $dep.revision
git -C $checkout checkout --detach $dep.revision
$actual = (git -C $checkout rev-parse HEAD).Trim()
if ($actual -ne $dep.revision) { throw "Pinned uploader revision mismatch: $actual" }

$runtimeConfig = Join-Path $checkout "conf.py"
if (-not (Test-Path $runtimeConfig)) {
  Copy-Item (Join-Path $checkout "conf.example.py") $runtimeConfig
}

if (-not $SkipPythonDependencies) {
  $venv = Join-Path $checkout ".venv"
  if (-not (Test-Path $venv)) { python -m venv $venv }
  $python = Join-Path $venv "Scripts\python.exe"
  & $python -m pip install --upgrade pip
  if (Test-Path (Join-Path $checkout "requirements.txt")) {
    & $python -m pip install -r (Join-Path $checkout "requirements.txt")
  }
  # Upstream's requirements.txt omits patchright while production modules import it.
  # Installing the package itself applies pyproject.toml and its pinned patchright dependency.
  & $python -m pip install -e $checkout
  & $python -m patchright install chromium
}

Write-Output ([pscustomobject]@{name="social-auto-upload"; revision=$actual; checkout=$checkout; ready=$true} | ConvertTo-Json)
