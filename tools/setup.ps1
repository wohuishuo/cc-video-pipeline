<#
.SYNOPSIS
  环境自检 / 补装。重复运行安全。
#>
$ErrorActionPreference = "Continue"
Write-Host "=== cc 视频环境自检 ===" -ForegroundColor Cyan

function Check($name, $cmd) {
  $c = Get-Command $cmd -ErrorAction SilentlyContinue
  if ($c) { Write-Host ("  [OK]   {0,-12} {1}" -f $name, $c.Source) -ForegroundColor Green }
  else { Write-Host ("  [MISS] {0,-12} 运行: scoop install {1}" -f $name, $cmd) -ForegroundColor Yellow }
}
Check "ffmpeg" "ffmpeg"
Check "yt-dlp" "yt-dlp"
Check "node"   "node"

$venv = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (Test-Path $venv) {
  # faster-whisper
  $fw = & $venv -c "import faster_whisper; print(faster_whisper.__version__)" 2>$null
  if ($fw) { Write-Host "  [OK]   faster-whisper $fw" -ForegroundColor Green }
  else { Write-Host "  [MISS] faster-whisper 未装: & '$venv' -m pip install faster-whisper" -ForegroundColor Yellow }

  # FunASR
  $fa = & $venv -c "import funasr; print(funasr.__version__)" 2>$null
  if ($fa) { Write-Host "  [OK]   FunASR      $fa" -ForegroundColor Green }
  else { Write-Host "  [MISS] FunASR 未装: & '$venv' -m pip install funasr torch" -ForegroundColor Yellow }

  # MediaPipe + OpenCV（人脸追踪横转竖 reframe.ps1 需要）
  $mp = & $venv -c "import mediapipe,cv2; print(mediapipe.__version__)" 2>$null
  if ($mp) { Write-Host "  [OK]   mediapipe   $mp (reframe 人脸追踪可用)" -ForegroundColor Green }
  else { Write-Host "  [MISS] mediapipe 未装: & '$venv' -m pip install mediapipe opencv-python" -ForegroundColor Yellow }

  # edge-tts（localize-video 配音需要）
  $et = & $venv -c "import edge_tts; print(edge_tts.__version__)" 2>$null
  if ($et) { Write-Host "  [OK]   edge-tts    $et (配音可用)" -ForegroundColor Green }
  else { Write-Host "  [MISS] edge-tts 未装: & '$venv' -m pip install edge-tts" -ForegroundColor Yellow }
}
else {
  Write-Host "  [MISS] venv 不存在。建: python3.12 -m venv tools\.venv; 然后 pip install faster-whisper funasr torch" -ForegroundColor Yellow
}

# QSV 硬件编码自检（Intel Arc）
$qsv = ffmpeg -hide_banner -encoders 2>$null | Select-String "h264_qsv"
if ($qsv) { Write-Host "  [OK]   Intel QSV 硬件编码可用 (h264_qsv / hevc_qsv)" -ForegroundColor Green }
else { Write-Host "  [WARN] 未检测到 QSV，剪辑将走 CPU 软编" -ForegroundColor Yellow }

Write-Host "=== 完成 ===" -ForegroundColor Cyan
