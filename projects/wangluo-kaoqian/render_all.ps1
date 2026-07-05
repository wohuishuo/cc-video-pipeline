# 渲染6个Part的"教学博客"风格视觉视频 + 合成纳西妲配音 -> final.mp4
# 前置：parts.json + 各 partN/narration.wav + partN/timings.json 已就绪，
#       root.tsx 已注册 exam-part1..exam-part6 这6个 composition。
$ErrorActionPreference = "Stop"
$env:npm_config_cache = "C:\Users\艾莉\.npm-cache"

$ProjRoot = "C:\Users\艾莉\Videos\cc视频剪辑"
$RemotionDir = Join-Path $ProjRoot "tools\remotion-hello"
$OutBase = Join-Path $ProjRoot "projects\wangluo-kaoqian"

Push-Location $RemotionDir
try {
    for ($i = 1; $i -le 6; $i++) {
        $partDir = Join-Path $OutBase "part$i"
        $visual = Join-Path $partDir "visual.mp4"
        $narration = Join-Path $partDir "narration.wav"
        $final = Join-Path $partDir "final.mp4"

        if (-not (Test-Path $narration)) {
            Write-Host "[skip] part$i 缺 narration.wav"
            continue
        }

        Write-Host "=== 渲染 exam-part$i 视觉 ==="
        npx remotion render src/root.tsx "exam-part$i" $visual
        if ($LASTEXITCODE -ne 0) { throw "render part$i failed" }

        Write-Host "=== 合成 part$i 配音 ==="
        if (Test-Path $final) { Remove-Item $final -Force }
        ffmpeg -y -i $visual -i $narration -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -ar 48000 -ac 2 -b:a 192k -shortest $final
        if ($LASTEXITCODE -ne 0) { throw "mux part$i failed" }

        Write-Host "[ok] part$i -> $final"
    }
} finally {
    Pop-Location
}
