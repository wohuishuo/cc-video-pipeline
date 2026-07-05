<#
.SYNOPSIS
  把 C:\Users\艾莉\Videos\cc视频剪辑\tools\weflow-src 从 hicccc77 切到 wohuishuo WeFlow
  main 分支，确保是你 fork 的最新。
#>

$env:npm_config_cache = "C:\Users\艾莉\.npm-cache"

cd C:\Users\艾莉\Videos\cc视频剪辑\tools\weflow-src

# 1. 切到你 fork 的 main
git remote set-url origin https://github.com/wohuishuo/WeFlow.git
git fetch origin
git switch main
git pull origin main --rebase

# 2. 清理
Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue

# 3. install
npm install
# 4. build win exe
npm run build