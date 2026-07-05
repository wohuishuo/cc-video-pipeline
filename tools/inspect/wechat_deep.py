#!/usr/bin/env python
"""深度检查: 给每个视频抽 3 帧(开头/中/末)，输出元数据 + 视频片段判断
用法: python inspect_deep.py <dir>
"""
import sys, subprocess, json
from pathlib import Path
from datetime import datetime

DIR = Path(sys.argv[1] if len(sys.argv) > 1 else
    r"C:\Users\艾莉\Documents\xwechat_files\wxid_d4uw3ea4rg8r22_31e4\msg\file\2026-06")
OUT = DIR / "_thumbs"
OUT.mkdir(exist_ok=True)

def grab(src, dst, t):
    subprocess.run(["ffmpeg","-y","-loglevel","error","-ss",str(t),"-i",str(src),
                    "-frames:v","1","-q:v","4",str(dst)],
                    capture_output=True, encoding="utf-8", errors="replace")

def probe(src):
    r = subprocess.run(["ffprobe","-v","error","-select_streams","a:0",
                        "-show_entries","stream=codec_name,channels,sample_rate",
                        "-show_entries","format=duration,size,bit_rate",
                        "-of","json",str(src)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    info = json.loads(r.stdout) if r.returncode == 0 else {}
    s = info.get("streams", [{}])[0]
    f = info.get("format", {})
    return {
        "duration": float(f.get("duration", 0)),
        "size_mb": int(f.get("size", 0)) / (1024*1024),
        "video_kbps": int(f.get("bit_rate", 0)) / 1000,
        "has_audio": bool(s),
        "audio_codec": s.get("codec_name", ""),
        "audio_channels": s.get("channels", 0),
    }

videos = sorted(DIR.glob("*.mp4"))
print(f"=== 12 视频深度检查 ===\n")
print(f"{'#':<3} {'时长':<6} {'大小':<8} {'码率':<6} {'音轨':<12} 文件")
print("-" * 80)
for i, v in enumerate(videos, 1):
    info = probe(v)
    dur = f"{int(info['duration']//60)}:{int(info['duration']%60):02d}"
    audio = f"{info['audio_codec']}/{info['audio_channels']}ch" if info['has_audio'] else "无音轨"
    print(f"{i:<3} {dur:<6} {info['size_mb']:>5.1f}MB {info['video_kbps']:>5.0f}k {audio:<12} {v.name[:50]}")
