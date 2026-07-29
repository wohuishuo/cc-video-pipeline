$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$commands = @("python", "git", "ffmpeg", "ffprobe", "yt-dlp", "node", "npm")
$results = foreach ($name in $commands) {
  $found = Get-Command $name -ErrorAction SilentlyContinue
  [pscustomobject]@{name=$name; ready=[bool]$found; path=if ($found) {$found.Source} else {$null}}
}
Push-Location $root
try {
  $python = Join-Path $root ".venv\Scripts\python.exe"
  if (-not (Test-Path $python)) { $python = "python" }
  & $python -m scripts.validate_mvp_manifests $root
  $manifestExit = $LASTEXITCODE
} finally { Pop-Location }
$payload = [pscustomobject]@{manifest_contract=($manifestExit -eq 0); dependencies=$results}
$payload | ConvertTo-Json -Depth 4
if ($manifestExit -ne 0) { exit $manifestExit }
