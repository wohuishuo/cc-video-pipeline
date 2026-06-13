# 列出应该被 git 提交的文件
$root = $PSScriptRoot

# 模拟 .gitignore 的 ignore 模式
$ignorePatterns = @(
    "*.venv*",
    "*node_modules*",
    "*site-packages*",
    "*reference\*\video.*",
    "*reference\*\audio.*",
    "*reference\*\*.info.json",
    "*reference\*\frames\*",
    "*\cookies.txt",
    "*reference\商业金融书单\frames\*",
    "*reference\曙光*\frames\*",
    "*reference\小Lin*",
    "*reference\曙光*",
    "_refs",
    "data/我",
    "projects/active"
)

function Should-Ignore($rel) {
    foreach ($p in $ignorePatterns) {
        if ($rel -like "*$p*") { return $true }
    }
    return $false
}

$all = Get-ChildItem -Path $root -Recurse -File -ErrorAction SilentlyContinue
$commit = @()
$ignore = @()
foreach ($f in $all) {
    $rel = $f.FullName.Substring($root.Length).TrimStart("\").Replace("\", "/")
    if (Should-Ignore $rel) {
        $ignore += $rel
    } else {
        $commit += $rel
    }
}

Write-Host "=== TRACKED FILES ($($commit.Count) would commit) ===" -ForegroundColor Green
$commit | Sort-Object | ForEach-Object { Write-Host "  $_" }
Write-Host ""
Write-Host "=== IGNORED ($($ignore.Count) files) ===" -ForegroundColor DarkGray
$ignore | Sort-Object | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
