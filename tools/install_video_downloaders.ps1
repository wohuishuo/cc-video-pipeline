param([switch]$SkipPythonDependencies)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$lock = Get-Content (Join-Path $root "vendor\video-uploaders.lock.json") -Raw | ConvertFrom-Json
$dep = $lock.dependencies.f2
$checkout = Join-Path $root $dep.checkout
if (-not (Test-Path (Join-Path $checkout ".git"))) {
  New-Item -ItemType Directory -Force (Split-Path -Parent $checkout) | Out-Null
  git clone --filter=blob:none $dep.url $checkout
}
git -C $checkout fetch --depth 1 origin $dep.revision
git -C $checkout checkout --detach $dep.revision
$actual = (git -C $checkout rev-parse HEAD).Trim()
if ($actual -ne $dep.revision) { throw "Pinned f2 revision mismatch: $actual" }
if (-not $SkipPythonDependencies) {
  $venv = Join-Path $checkout ".venv"
  if (-not (Test-Path $venv)) { python -m venv $venv }
  $python = Join-Path $venv "Scripts\python.exe"
  & $python -m pip install --upgrade pip
  & $python -m pip install -e $checkout
}
Write-Output ([pscustomobject]@{name="f2"; revision=$actual; checkout=$checkout; ready=$true} | ConvertTo-Json)
