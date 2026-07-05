<#
.SYNOPSIS
  Cos 跳舞批处理：对源目录下每条竖屏视频 → 节拍标记 + 调色 + 封面，独立输出。
.EXAMPLE
  .\cos_batch.ps1 -SrcDir "C:\...\2026-06" -OutRoot ".\projects\cos-2026-06" -Strength med
#>
param(
  [Parameter(Mandatory = $true)][string]$SrcDir,
  [Parameter(Mandatory = $true)][string]$OutRoot,
  [ValidateSet("low","med","high")][string]$Strength = "med",
  [string]$Root = "C:\Users\艾莉\Videos\cc视频剪辑"
)
$ErrorActionPreference = "Continue"
$py = "$root\tools\.venv\Scripts\python.exe"
$grade = "$root\.claude\skills\edit-ffmpeg\scripts\color_grade.ps1"
New-Item -ItemType Directory -Force $OutRoot | Out-Null
$clips = Get-ChildItem "$SrcDir\*.mp4" | Sort-Object Name
Write-Host "===== Cos 批处理: $($clips.Count) 条 =====" -ForegroundColor Cyan

$i = 0
foreach ($c in $clips) {
  $i++
  $slug = $c.BaseName
  $proj = Join-Path $OutRoot $slug
  New-Item -ItemType Directory -Force $proj | Out-Null
  Write-Host "`n[$i/$($clips.Count)] $slug" -ForegroundColor Yellow

  # 1) 节拍标记
  & $py "$root\tools\beat_detect.py" $c.FullName --out-dir $proj 2>&1 | Select-String "\[ok\]|\[err\]"
  # 2) 调色
  & $grade -Video $c.FullName -Out "$proj\graded.mp4" -Strength $Strength 2>&1 | Select-String "\[ok\]|\[warn\]"
  # 3) 封面
  & $py "$root\tools\pick_cover.py" $c.FullName --out "$proj\cover.jpg" 2>&1 | Select-String "\[ok\]"
}
Write-Host "`n===== 完成 → $OutRoot =====" -ForegroundColor Cyan
