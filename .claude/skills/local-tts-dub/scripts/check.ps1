param([switch]$Json)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
$prod = Join-Path $root 'tools\tts-mvp'
$fork = Join-Path $root 'projects\qwen3-tts-xpu-v5-fork'
$py = Join-Path $prod '.venv\Scripts\python.exe'
$ref = Join-Path $prod 'voices\纳西妲_zh\ready\vo_dialog_LLZAQ004_nahida_01.wav'
$models = @(
  Join-Path $prod 'models\Qwen3-TTS-12Hz-0.6B-Base'
  Join-Path $prod 'models\Qwen3-TTS-12Hz-0.6B-CustomVoice'
)

$result = [ordered]@{
  production_python = Test-Path $py
  base_model = Test-Path $models[0]
  custom_voice_model = Test-Path $models[1]
  nahida_reference = Test-Path $ref
  ffmpeg = [bool](Get-Command ffmpeg -ErrorAction SilentlyContinue)
  xpu_fork = Test-Path (Join-Path $fork 'run_benchmark.ps1')
  torch = $null
  transformers = $null
  xpu_available = $false
  production_route = 'CPU (stable)'
  xpu_route = 'EXPERIMENT ONLY: EOS unresolved'
}

if ($result.production_python) {
  $probe = & $py -c "import json,torch,transformers; print(json.dumps({'torch':torch.__version__,'transformers':transformers.__version__,'xpu':bool(hasattr(torch,'xpu') and torch.xpu.is_available())}))" 2>$null
  if ($LASTEXITCODE -eq 0 -and $probe) {
    $p = $probe | ConvertFrom-Json
    $result.torch = $p.torch
    $result.transformers = $p.transformers
    $result.xpu_available = $p.xpu
  }
}

if ($Json) { $result | ConvertTo-Json; exit }
$result.GetEnumerator() | ForEach-Object {
  $mark = if ($_.Value -eq $true) {'[ok]'} elseif ($_.Value -eq $false) {'[--]'} else {'[i] '}
  Write-Host "$mark $($_.Key): $($_.Value)"
}
if (-not ($result.production_python -and $result.base_model -and $result.nahida_reference -and $result.ffmpeg)) {
  Write-Warning '生产配音依赖不完整，请先修复 [--] 项。'
  exit 1
}
Write-Host '[ready] 稳定生产配音可用；XPU fork 仍只用于实验。' -ForegroundColor Green
