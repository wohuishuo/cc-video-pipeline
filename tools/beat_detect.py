#!/usr/bin/env python
"""节拍检测 / 卡点标记。给 Cos 跳舞视频用——检测音乐节拍，输出卡点时间点。

用法:
    python beat_detect.py <视频或音频> [--out-dir DIR] [--tightness 100]

输出（写到 --out-dir，默认输入同目录）:
    <stem>.beats.json  — tempo + 每拍时间 + 重拍(downbeat) + 八拍点
    <stem>.beats.txt   — 每行一个拍点秒数（人读 / 喂给剪辑脚本）

说明:
    - tempo=BPM；beats=每一拍；downbeats=每小节第一拍(4/4)；eight=每8拍(一个"八拍")
    - 卡点常用：转场/特效卡在 downbeat，大动作卡在 eight 的起点
    - 非 ASCII 路径安全：内部用 ffmpeg 抽 wav，cv2/librosa 都读这个临时 wav
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import librosa


def extract_wav(src: Path, dst: Path):
    subprocess.run(
        ["ffmpeg", "-nostdin", "-y", "-i", str(src),
         "-vn", "-ac", "1", "-ar", "22050", str(dst)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--tightness", type=float, default=100.0,
                    help="beat_track 紧致度，越大越贴节拍器（默认100）")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.exists():
        sys.exit(f"[err] 文件不存在: {src}")
    outdir = Path(args.out_dir) if args.out_dir else src.parent
    outdir.mkdir(parents=True, exist_ok=True)

    # 抽音频到临时 wav（避开非 ASCII 路径 + 统一采样率）
    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "a.wav"
        extract_wav(src, wav)
        y, sr = librosa.load(str(wav), sr=22050, mono=True)

    dur = len(y) / sr
    # 节拍跟踪
    tempo, beat_frames = librosa.beat.beat_track(
        y=y, sr=sr, tightness=args.tightness, units="frames")
    beats = librosa.frames_to_time(beat_frames, sr=sr).tolist()
    tempo = float(np.atleast_1d(tempo)[0])

    # 重拍(downbeat) 估计：找每 4 拍里 onset 最强的相位作为小节起点
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    beat_strength = []
    for bf in beat_frames:
        i = min(int(bf), len(onset_env) - 1)
        beat_strength.append(float(onset_env[i]))
    best_phase, best_sum = 0, -1
    for phase in range(4):
        s = sum(beat_strength[phase::4])
        if s > best_sum:
            best_sum, best_phase = s, phase
    downbeats = beats[best_phase::4]
    eights = beats[best_phase::8]

    out = {
        "source": src.name,
        "duration": round(dur, 2),
        "tempo_bpm": round(tempo, 1),
        "beat_count": len(beats),
        "beats": [round(b, 3) for b in beats],
        "downbeats": [round(b, 3) for b in downbeats],
        "eight_counts": [round(b, 3) for b in eights],
    }
    stem = src.stem
    (outdir / f"{stem}.beats.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    (outdir / f"{stem}.beats.txt").write_text(
        "\n".join(f"{b:.3f}" for b in beats), encoding="utf-8")
    print(f"[ok] {src.name}: {tempo:.0f}BPM, {len(beats)}拍, "
          f"{len(downbeats)}个重拍, {len(eights)}个八拍点 -> {stem}.beats.json/txt",
          file=sys.stderr)


if __name__ == "__main__":
    main()
