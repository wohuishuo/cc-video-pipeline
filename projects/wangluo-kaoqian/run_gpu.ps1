# 激活 MSVC 环境(cl.exe/INCLUDE/LIB) 后跑 XPU+compile 合成
# 用法: .\run_gpu.ps1 -Part 3   (不带Part则跑全部)
param([string]$Part = "")

$ErrorActionPreference = "Stop"
$py = "C:\Users\艾莉\Videos\cc视频剪辑\tools\tts-mvp\.venv\Scripts\python.exe"

# 找 vcvars64.bat
$vcvars = Get-ChildItem "C:\Program Files*\Microsoft Visual Studio\2022\*\VC\Auxiliary\Build\vcvars64.bat" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $vcvars) {
    Write-Error "找不到 vcvars64.bat —— MSVC Build Tools 没装好"
    exit 1
}
Write-Host "[vcvars] $($vcvars.FullName)"

# 激活 vcvars64 并把它设置的环境变量灌进当前 PowerShell 会话
cmd /c "`"$($vcvars.FullName)`" >nul 2>&1 && set" | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        Set-Item "env:$($matches[1])" $matches[2]
    }
}

# 验证 cl.exe 现在可见
$cl = Get-Command cl.exe -ErrorAction SilentlyContinue
if ($cl) { Write-Host "[ok] cl.exe -> $($cl.Source)" } else { Write-Error "cl.exe 仍不可见"; exit 1 }

# inductor 用到的环境（可选，帮助 triton/xpu）
$env:TORCHINDUCTOR_COMPILE_THREADS = "8"

Push-Location "C:\Users\艾莉\Videos\cc视频剪辑\projects\wangluo-kaoqian"
try {
    & $py synth_gpu.py $Part
} finally {
    Pop-Location
}
