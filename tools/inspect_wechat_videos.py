#!/usr/bin/env python
"""检查微信里下载的 cos/跳舞 视频，输出每个的：时长/大小/分辨率/前几秒抽帧。
用法: python inspect_wechat_videos.py <dir>
"""
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime

VIDEO_DIR = Path(sys.argv[1] if len(sys.argv) > 1
    else r"C:\Users\艾莉\Documents\xwechat_files\wxid_d4uw3ea4rg8r22_31e4\msg\file\2026-06")

def ffprobe(path: Path) -> dict:
    """ffprobe 拿视频元信息"""
    out = subprocess.run([
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,duration,nb_frames,codec_name",
        "-show_entries", "format=duration,size,bit_rate",
        "-of", "json",
        str(path)
    ], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if out.returncode != 0:
        return {}
    return json.loads(out.stdout)

def grab_thumb(path: Path, out: Path, t: float = 0.5):
    """从 t 秒处抽一帧"""
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", str(t), "-i", str(path),
        "-frames:v", "1", "-q:v", "5", str(out)
    ], capture_output=True, encoding="utf-8", errors="replace")


videos = sorted(VIDEO_DIR.glob("*.mp4"))
print(f"=== 扫描 {VIDEO_DIR} ===\n")
print(f"找到 {len(videos)} 个视频:\n")
print(f"{'#':<3} {'文件':<35} {'时长':<8} {'分辨率':<10} {'大小':<10} {'修改日期':<12}")
print("-" * 90)

data = []
for i, v in enumerate(videos, 1):
    info = ffprobe(v)
    stream = info.get("streams", [{}])[0] if info.get("streams") else {}
    fmt = info.get("format", {})

    dur = float(fmt.get("duration", 0))
    w = stream.get("width", "?")
    h = stream.get("height", "?")
    size_bytes = int(fmt.get("size", v.stat().st_size))
    size_mb = size_bytes / (1024*1024)
    dur_str = f"{int(dur//60)}:{int(dur%60):02d}" if dur > 0 else "?"
    res = f"{w}x{h}"
    mtime = datetime.fromtimestamp(v.stat().st_mtime).strftime("%Y-%m-%d %H:%M")

    print(f"{i:<3} {v.name[:33]:<35} {dur_str:<8} {res:<10} {size_mb:>6.1f}MB   {mtime}")

    data.append({
        "i": i,
        "name": v.name,
        "path": str(v),
        "duration": dur,
        "width": w,
        "height": h,
        "size_mb": round(size_mb, 2),
        "mtime": mtime,
    })

# 给每个视频抽 1 帧缩略图到临时目录
print(f"\n=== 抽缩略图 ===")
thumb_dir = VIDEO_DIR / "_thumbs"
thumb_dir.mkdir(exist_ok=True)
for d in data:
    out = thumb_dir / f"thumb_{d['i']:02d}.jpg"
    if not out.exists():
        grab_thumb(Path(d["path"]), out, t=0.5)
        print(f"  [ok] thumb_{d['i']:02d}.jpg  ({d['name'][:40]})")
    else:
        print(f"  [skip] thumb_{d['i']:02d}.jpg 已存在")
print(f"\n  位置: {thumb_dir}")
