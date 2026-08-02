$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = $null
$gitCommon = (& git -C $root rev-parse --git-common-dir 2>$null)
if ($LASTEXITCODE -eq 0 -and $gitCommon) {
  $commonPath = if ([IO.Path]::IsPathRooted($gitCommon.Trim())) { (Resolve-Path $gitCommon.Trim()).Path } else { (Resolve-Path (Join-Path $root $gitCommon.Trim())).Path }
  $candidate = Join-Path (Split-Path -Parent $commonPath) "tools\.venv\Scripts\python.exe"
  if (Test-Path -LiteralPath $candidate) { $python = $candidate }
}
if (-not $python) {
  $candidate = Join-Path $root ".venv\Scripts\python.exe"
  $python = if (Test-Path -LiteralPath $candidate) { $candidate } else { "python" }
}
Push-Location $root
try {
  $suites = @(
    "tests\transcription_mvp",
    "tests\source_intake",
    "tests\video_graph_studio",
    "tests\repository",
    "tests\research_mvp",
    "tests\video_platform",
    "tests\localization\test_edge_video_localizer.py",
    "tests\translation_mvp",
    "tests\voice_rendering_mvp",
    "tests\localization_mvp",
    "tests\creator_discovery_mvp",
    "tests\publication_mvp",
    "tests\workspace_access_mvp",
    "tests\workspace_storage_mvp",
    "tests\credential_vault_mvp"
  )
  & $python -m pytest --import-mode=importlib @suites -q
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  & $python scripts\validate_mvp_manifests.py .
  exit $LASTEXITCODE
} finally { Pop-Location }
