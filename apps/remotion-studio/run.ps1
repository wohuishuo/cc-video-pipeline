param([Parameter(Position=0)][ValidateSet("studio","render")][string]$Command="studio",[Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments)
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$studio = Join-Path $root "tools\remotion-hello"
Push-Location $studio
try {
  if ($Command -eq "studio") { & npx remotion studio src/root.tsx @Arguments }
  else { & npx remotion render src/root.tsx @Arguments }
  exit $LASTEXITCODE
} finally { Pop-Location }
