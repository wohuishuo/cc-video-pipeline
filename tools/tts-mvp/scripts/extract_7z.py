# 解压脚本: 从原神 7z 抓指定角色 wav → 平铺到 ready
# 用法: python extract_7z.py <角色中文名> <7z 文件> [角色输出目录]
# 例: python extract_7z.py 纳西妲 "D:\BaiduNetdiskDownload\原神\【原神】须弥.7z"
# 例: python extract_7z.py 七七   "D:\BaiduNetdiskDownload\原神\【原神】璃月.7z"
import subprocess
import sys
from pathlib import Path

if len(sys.argv) < 3:
    print("用法: python extract_7z.py <角色> <7z文件> [输出目录]")
    print("  角色如: 纳西妲 / 七七 / 甘雨")
    print("  7z文件如: D:\\BaiduNetdiskDownload\\原神\\【原神】须弥.7z")
    sys.exit(1)

CHAR = sys.argv[1]
ARC = Path(sys.argv[2])
OUT_BASE = Path(sys.argv[3]) if len(sys.argv) > 3 else Path(
    r"C:\Users\艾莉\Videos\cc视频剪辑\tools\tts-mvp\voices"
)
CHAR_DIR = OUT_BASE / f"{CHAR}_zh"
TMP = CHAR_DIR / "_from_7z"
READY = CHAR_DIR / "ready"

CHAR_DIR.mkdir(parents=True, exist_ok=True)
TMP.mkdir(parents=True, exist_ok=True)
READY.mkdir(parents=True, exist_ok=True)

# 取 7z 内含该角色的根目录: 例如 【原神】须弥
# 不用 split 解析, 直接用 ARC 的 stem 重建
stem = ARC.stem  # "【原神】须弥"
prefix_match = stem
print(f"[info] 角色={CHAR}, 7z={ARC.name}, prefix={prefix_match}")

# 7z 解压: 用 -ir! 包含
cmd = [
    "7z", "x", "-y", f"-o{TMP}", str(ARC),
    f"-ir!{prefix_match}\\reference_audios\\randoms\\{CHAR}\\*",
    f"-ir!{prefix_match}\\reference_audios\\emotions\\{CHAR}\\*",
]
print(f"[run] 7z x ... {CHAR}\\* ...")
r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
# 输出只取最后非空行
for line in (r.stdout or "").splitlines()[-5:]:
    print(f"  {line}")
if r.returncode != 0:
    print(f"[warn] 7z 退出码 {r.returncode}, 继续")

# 平铺 wav 和 lab
n = 0
for f in TMP.rglob("*"):
    if f.suffix.lower() in (".wav", ".lab"):
        dest = READY / f.name
        if not dest.exists():
            dest.write_bytes(f.read_bytes())
            n += 1

# 清理 TMP (用 cmd rmdir 绕开 PowerShell 保护路径问题)
import subprocess
subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", str(TMP)], check=False)
TMP.rmdir() if TMP.exists() else None  # 留个保险
# 统计
wavs = list(READY.glob("*.wav"))
total_mb = sum(w.stat().st_size for w in wavs) / 1024 / 1024
print(f"[ok] {CHAR}: {len(wavs)} wav → {READY}  ({total_mb:.1f} MB)")
print(f"     示例: {wavs[0].name if wavs else '(none)'}")
