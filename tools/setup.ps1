<#
.SYNOPSIS
  环境自检 / 补装。重复运行安全。
  任何时候接手这个项目，先跑这个看什么在工作。
  详细版本见 tools/health_check.ps1
#>
$ErrorActionPreference = "Continue"
Write-Host "=== cc 视频环境自检 ===" -ForegroundColor Cyan

# 1) 系统级工具
function Check($name, $cmd) {
  $c = Get-Command $cmd -ErrorAction SilentlyContinue
  if ($c) { Write-Host ("  [OK]   {0,-12} {1}" -f $name, $c.Source) -ForegroundColor Green }
  else { Write-Host ("  [MISS] {0,-12} 运行: scoop install {1}" -f $name, $cmd) -ForegroundColor Yellow }
}
Check "ffmpeg" "ffmpeg"
Check "yt-dlp" "yt-dlp"
Check "node"   "node"
Check "gh"     "gh"
Check "git"    "git"

# 2) AI 库（venv）
$venv = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (Test-Path $venv) {
    $libs = @{
        "faster-whisper"  = "import faster_whisper; print(faster_whisper.__version__)"
        "FunASR"          = "import funasr; print(funasr.__version__)"
        "torch"            = "import torch; print(torch.__version__)"
        "bilibili-api"     = "import bilibili_api; print('ok')"
        "edge-tts"         = "import edge_tts; print(edge_tts.__version__)"
        "mediapipe"        = "import mediapipe; print(mediapipe.__version__)"
        "opencv"           = "import cv2; print(cv2.__version__)"
    }
    foreach ($name in $libs.Keys) {
        $cmd = $libs[$name]
        $out = & $venv -c $cmd 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) {
            Write-Host ("  [OK]   {0,-18} {1}" -f $name, ($out | Select-Object -First 1).Trim()) -ForegroundColor Green
        } else {
            $cmd_install = switch ($name) {
                "faster-whisper"  { "pip install faster-whisper" }
                "FunASR"          { "pip install funasr" }
                "torch"            { "pip install torch --index-url https://download.pytorch.org/whl/cpu" }
                "bilibili-api"     { "pip install bilibili-api-python" }
                "edge-tts"         { "pip install edge-tts" }
                "mediapipe"        { "pip install mediapipe opencv-python" }
                default            { "pip install $name" }
            }
            Write-Host ("  [MISS] {0,-18} 装: {1} (在 venv 下)" -f $name, $cmd_install) -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  [MISS] venv 不存在。" -ForegroundColor Yellow
    Write-Host "         装: python3.12 -m venv tools\.venv; 然后 pip install" -ForegroundColor Yellow
    Write-Host "         完整命令见 INSTALL_HISTORY.md 第 7 节" -ForegroundColor Yellow
}

# 3) 硬件加速
$qsv = ffmpeg -hide_banner -encoders 2>$null | Select-String "h264_qsv"
if ($qsv) { Write-Host "  [OK]   Intel QSV 硬件编码可用 (h264_qsv / hevc_qsv)" -ForegroundColor Green }
else { Write-Host "  [WARN] 未检测到 QSV，剪辑将走 CPU 软编" -ForegroundColor Yellow }

# 4) Remotion
$remDir = Join-Path (Split-Path $PSScriptRoot -Parent) "tools\remotion-hello"
if (Test-Path (Join-Path $remDir "node_modules")) {
    Write-Host "  [OK]   Remotion node_modules 已装" -ForegroundColor Green
} else {
    Write-Host "  [MISS] Remotion 依赖未装: cd $remDir; npm install" -ForegroundColor Yellow
}

# 5) 凭据
$rootDir = Split-Path (Split-Path $PSCommandPath) -Parent
$cookies = Join-Path $rootDir "reference\cookies.txt"
if (Test-Path $cookies) {
    Write-Host "  [OK]   B站 cookies.txt 在位" -ForegroundColor Green
} else {
    Write-Host "  [WARN] B站 cookies.txt 缺失（B站下载需要；详见 INSTALL_HISTORY.md 第 5 节）" -ForegroundColor Yellow
}

# 6) MCP（CCD）
$cfg = Join-Path $env:APPDATA "Claude\claude_desktop_config.json"
if (Test-Path $cfg) {
    $j = Get-Content $cfg -Raw | ConvertFrom-Json -ErrorAction SilentlyContinue
    if ($j.mcpServers) {
        Write-Host "  [OK]   CCD MCP servers:" -ForegroundColor Green
        $j.mcpServers.PSObject.Properties | ForEach-Object { Write-Host "        - $($_.Name)" -ForegroundColor Cyan }
    }
} else {
    Write-Host "  [MISS] CCD 配置文件不存在" -ForegroundColor Yellow
}

Write-Host "=== 完成 ===" -ForegroundColor Cyan
Write-Host "完整工具清单: INSTALL_HISTORY.md" -ForegroundColor DarkGray
Write-Host "工具速查: TOOLS.md" -ForegroundColor DarkGray
Write-Host "项目笔记: CLAUDE.md" -ForegroundColor DarkGray
