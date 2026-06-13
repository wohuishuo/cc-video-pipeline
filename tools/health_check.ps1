Write-Host "========== System tools ==========" -ForegroundColor Cyan
function Check($name, $cmd) {
  $c = Get-Command $cmd -ErrorAction SilentlyContinue
  if ($c) { Write-Host ("  [OK]   {0,-12} {1}" -f $name, $c.Source) -ForegroundColor Green }
  else { Write-Host ("  [MISS] {0,-12}" -f $name) -ForegroundColor Yellow }
}
Check "ffmpeg" "ffmpeg"
Check "yt-dlp" "yt-dlp"
Check "node" "node"
Check "npm" "npm"
Check "gh" "gh"
Check "git" "git"
Check "scoop" "scoop"
Check "python3.12" "python3.12"
Check "python" "python"

Write-Host ""
Write-Host "========== System Python (3.14, AI libs unavailable here) ==========" -ForegroundColor Yellow
& python --version 2>&1 | Out-String
& python -c "import sys; print('Path:', sys.executable)" 2>&1 | Out-String

Write-Host ""
Write-Host "========== AI libs (venv) ==========" -ForegroundColor Cyan
$venv = "C:\Users\艾莉\Videos\cc视频剪辑\tools\.venv\Scripts\python.exe"
$libs = @(
    @{name="faster-whisper";  cmd="import faster_whisper; print(faster_whisper.__version__)"},
    @{name="FunASR";          cmd="import funasr; print(funasr.__version__)"},
    @{name="torch";            cmd="import torch; print(torch.__version__)"},
    @{name="torchaudio";       cmd="import torchaudio; print(torchaudio.__version__)"},
    @{name="bilibili-api";     cmd="import bilibili_api; print('17.4.1')"},
    @{name="edge-tts";         cmd="import edge_tts; print(edge_tts.__version__)"},
    @{name="mediapipe";        cmd="import mediapipe; print(mediapipe.__version__)"},
    @{name="opencv";           cmd="import cv2; print(cv2.__version__)"},
    @{name="yt-dlp (python)"; cmd="import yt_dlp; print(yt_dlp.version.__version__)"}
)
foreach ($l in $libs) {
    $out = & $venv -c $l.cmd 2>&1
    $ver = ($out | Select-Object -First 1) -as [string]
    if ($LASTEXITCODE -eq 0 -and $ver) {
        Write-Host ("  [OK]   {0,-18} {1}" -f $l.name, $ver.Trim()) -ForegroundColor Green
    } else {
        Write-Host ("  [MISS] {0,-18} ({1})" -f $l.name, ($out -join "; ")) -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "========== Hardware (Intel Arc QSV) ==========" -ForegroundColor Cyan
$qsv = ffmpeg -hide_banner -encoders 2>$null | Select-String "h264_qsv"
if ($qsv) { Write-Host "  [OK]   h264_qsv / hevc_qsv available" -ForegroundColor Green }
else { Write-Host "  [MISS] QSV unavailable — will fall back to CPU libx264" -ForegroundColor Yellow }

Write-Host ""
Write-Host "========== Remotion ==========" -ForegroundColor Cyan
$remDir = "C:\Users\艾莉\Videos\cc视频剪辑\tools\remotion-hello"
if (Test-Path $remDir) {
    Write-Host "  [OK]   $remDir exists" -ForegroundColor Green
    if (Test-Path "$remDir\node_modules") {
        Write-Host "  [OK]   node_modules installed" -ForegroundColor Green
    } else {
        Write-Host "  [MISS] node_modules not installed — run npm install" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [MISS] project dir missing" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========== Node/npm global ==========" -ForegroundColor Cyan
& node --version 2>&1 | Out-String
& npm --version 2>&1 | Out-String
Write-Host "  npm cache: $(npm config get cache 2>$null)" -ForegroundColor Gray

Write-Host ""
Write-Host "========== External MCP/CCD config ==========" -ForegroundColor Cyan
$claudeCfg = "C:\Users\艾莉\AppData\Local\Claude\claude_desktop_config.json"
if (Test-Path $claudeCfg) {
    Write-Host "  [OK]   $claudeCfg" -ForegroundColor Green
    $mcp = Get-Content $claudeCfg -Raw | ConvertFrom-Json -ErrorAction SilentlyContinue
    if ($mcp.mcpServers) {
        Write-Host "  MCP servers configured:" -ForegroundColor Cyan
        $mcp.mcpServers.PSObject.Properties | ForEach-Object {
            Write-Host "    - $($_.Name)"
        }
    } else {
        Write-Host "  [WARN] no MCP servers" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [MISS] CCD config missing" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========== Credentials ==========" -ForegroundColor Cyan
$cookies = "C:\Users\艾莉\Videos\cc视频剪辑\reference\cookies.txt"
if (Test-Path $cookies) {
    Write-Host "  [OK]   B站 cookies.txt present" -ForegroundColor Green
} else {
    Write-Host "  [MISS] B站 cookies.txt missing" -ForegroundColor Yellow
}
