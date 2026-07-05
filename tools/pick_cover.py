#!/usr/bin/env python
"""选封面帧：从视频里挑最清晰、有人脸、不过暗的一帧做封面（竖屏 cos 跳舞向）。

用法:
    python pick_cover.py <视频> [--out cover.jpg] [--skip-ends 0.1]

打分 = 清晰度(拉普拉斯方差) × 人脸加成 × 亮度合理性。
避开首尾 skip-ends 比例（准备动作/收尾）。
非 ASCII 路径安全：ffmpeg 抽帧到临时目录，cv2 用 imdecode 读。
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np


def probe_dur(p: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(p)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    return float(r.stdout.strip())


def imread_u(p):  # 读非 ASCII 路径
    return cv2.imdecode(np.fromfile(str(p), dtype=np.uint8), cv2.IMREAD_COLOR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--out", default=None)
    ap.add_argument("--skip-ends", type=float, default=0.1)
    ap.add_argument("--fps", type=float, default=3.0, help="候选帧采样率")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.exists():
        sys.exit(f"[err] 文件不存在: {src}")
    out = Path(args.out) if args.out else src.with_suffix(".cover.jpg")
    dur = probe_dur(src)
    t0, t1 = dur * args.skip_ends, dur * (1 - args.skip_ends)

    # 人脸检测器（OpenCV haar）。cv2 的 FileStorage 打不开非 ASCII 路径(艾莉/视频)，
    # 改成从内存读 XML 绕过；读不到就降级（只用清晰度+亮度，不加人脸权重）。
    face_cascade = None
    try:
        xml = Path(cv2.data.haarcascades + "haarcascade_frontalface_default.xml").read_text(encoding="utf-8")
        fs = cv2.FileStorage(xml, cv2.FileStorage_READ | cv2.FileStorage_MEMORY)
        c = cv2.CascadeClassifier()
        c.read(fs.getFirstTopLevelNode())
        if not c.empty():
            face_cascade = c
    except Exception as e:
        print(f"[warn] 人脸检测不可用，降级用清晰度: {e}", file=sys.stderr)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        subprocess.run(
            ["ffmpeg", "-nostdin", "-y", "-ss", f"{t0:.2f}", "-to", f"{t1:.2f}",
             "-i", str(src), "-vf", f"fps={args.fps},scale=360:-1",
             "-q:v", "3", str(td / "c_%04d.jpg")],
            check=True, stderr=subprocess.DEVNULL)
        frames = sorted(td.glob("c_*.jpg"))
        if not frames:
            sys.exit("[err] 没抽到候选帧")

        best_i, best_score = -1, -1.0
        for i, fp in enumerate(frames):
            img = imread_u(fp)
            if img is None:
                continue
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            sharp = cv2.Laplacian(gray, cv2.CV_64F).var()      # 清晰度
            bright = gray.mean()
            bright_ok = 1.0 if 50 <= bright <= 210 else 0.5    # 太暗/太亮降权
            face_bonus = 1.0
            if face_cascade is not None:
                faces = face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(40, 40))
                if len(faces) > 0:
                    fa = max(w * h for (x, y, w, h) in faces)
                    face_bonus = 1.5 + min(fa / (gray.shape[0] * gray.shape[1]) * 3, 1.0)
            score = sharp * bright_ok * face_bonus
            if score > best_score:
                best_score, best_i = score, i

        # 对应时间戳
        best_t = t0 + best_i / args.fps
        # 全分辨率抽该帧做封面
        subprocess.run(
            ["ffmpeg", "-nostdin", "-y", "-ss", f"{best_t:.2f}", "-i", str(src),
             "-frames:v", "1", "-q:v", "2", str(out)],
            check=True, stderr=subprocess.DEVNULL)
    print(f"[ok] {src.name}: 封面@{best_t:.1f}s (score={best_score:.0f}) -> {out.name}",
          file=sys.stderr)
    print(f"{best_t:.2f}")


if __name__ == "__main__":
    main()
