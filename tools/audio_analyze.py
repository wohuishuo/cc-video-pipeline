#!/usr/bin/env python
"""音频精细分析：BGM 床 / 音效(SFX) / 能量节奏。给参考视频拆解用。

核心思路（针对"人声口播+BGM+音效"类视频）：
  - 人声基本居中(L≈R)，BGM/音效多为立体声 → 用 side 声道(L-R)能量判 BGM 在不在
  - 人声几乎没有超低频(<120Hz)，音乐的 bass 有 → 超低频能量佐证 BGM
  - 音效(SFX)是短促瞬态 → onset 检测，尤其落在镜头切点附近的是转场音效
  - 整体 RMS 包络 → 找高潮/留白

用法:
  python audio_analyze.py <立体声wav> [--cuts cuts.txt] [--out out.json] [--hop 0.5]

输出 JSON：逐时间窗的 rms_db / bgm_score / 是否有 BGM；SFX 列表；BGM 段落；与切点的对齐。
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import librosa


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--cuts", default=None, help="cuts.txt（每行一个切点秒数）")
    ap.add_argument("--out", default=None)
    ap.add_argument("--hop", type=float, default=0.5, help="时间窗(秒)")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.exists():
        sys.exit(f"[err] 文件不存在: {src}")

    # 保留立体声
    y, sr = librosa.load(str(src), sr=44100, mono=False)
    if y.ndim == 1:
        y = np.vstack([y, y])  # 单声道也能跑，但 side 信息为 0
    L, R = y[0], y[1]
    mid = (L + R) / 2
    side = (L - R) / 2
    dur = len(mid) / sr
    hop = int(args.hop * sr)

    def frame_rms(x):
        n = len(x) // hop
        return np.array([np.sqrt(np.mean(x[i*hop:(i+1)*hop]**2) + 1e-12) for i in range(n)])

    rms_mid = frame_rms(mid)
    rms_side = frame_rms(side)

    # 超低频(20-120Hz)能量：人声几乎没有，音乐 bass 有
    S = np.abs(librosa.stft(mid, n_fft=2048, hop_length=hop))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
    lowband = (freqs >= 20) & (freqs <= 120)
    low_energy = S[lowband].mean(axis=0)
    low_energy = low_energy[:len(rms_mid)]
    rms_side = rms_side[:len(rms_mid)]

    # 归一化打分
    def norm(x):
        x = np.asarray(x)
        p95 = np.percentile(x, 95) + 1e-9
        return np.clip(x / p95, 0, 1)

    side_score = norm(rms_side)
    low_score = norm(low_energy)
    # BGM 分数：立体声成分 + 超低频，任一高即可能有 BGM
    bgm_score = np.maximum(side_score * 0.6 + low_score * 0.4, side_score * 0.5)
    bgm_on = bgm_score > 0.18  # 阈值：经验值

    rms_db = 20 * np.log10(norm(rms_mid) + 1e-6)
    times = np.arange(len(rms_mid)) * args.hop

    # BGM 连续段
    bgm_segs = []
    i = 0
    while i < len(bgm_on):
        if bgm_on[i]:
            j = i
            while j < len(bgm_on) and bgm_on[j]:
                j += 1
            if (j - i) * args.hop >= 1.0:  # 至少1秒
                bgm_segs.append([round(times[i], 1), round(times[min(j, len(times)-1)], 1)])
            i = j
        else:
            i += 1

    # SFX：full-mix onset（强瞬态）
    onset_env = librosa.onset.onset_strength(y=mid, sr=sr, hop_length=512)
    onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr,
                                        hop_length=512, units="time",
                                        delta=0.5, wait=10)
    # 节拍/速度（若有稳定 BGM）
    try:
        tempo = float(librosa.beat.tempo(onset_envelope=onset_env, sr=sr, hop_length=512)[0])
    except Exception:
        tempo = 0.0

    # 切点对齐
    cuts = []
    if args.cuts and Path(args.cuts).exists():
        cuts = [float(x) for x in Path(args.cuts).read_text().split() if x.strip()]
    # 落在切点 ±0.4s 内的 onset = 转场音效
    transition_sfx = []
    for c in cuts:
        near = [o for o in onsets if abs(o - c) <= 0.4]
        if near:
            transition_sfx.append(round(c, 2))

    bgm_pct = 100.0 * np.mean(bgm_on)
    out = {
        "source": src.name,
        "duration": round(dur, 1),
        "hop_sec": args.hop,
        "bgm_coverage_pct": round(bgm_pct, 1),
        "estimated_tempo_bpm": round(tempo, 1),
        "bgm_segments": bgm_segs,
        "onset_count": len(onsets),
        "onsets": [round(float(o), 2) for o in onsets],
        "transition_sfx_at_cuts": transition_sfx,
        "timeline": [
            {"t": round(float(times[i]), 1),
             "rms_db": round(float(rms_db[i]), 1),
             "bgm_score": round(float(bgm_score[i]), 2),
             "bgm": bool(bgm_on[i])}
            for i in range(len(rms_mid))
        ],
    }
    outp = Path(args.out) if args.out else src.with_suffix(".audio.json")
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] BGM覆盖={bgm_pct:.0f}% tempo={tempo:.0f}bpm "
          f"BGM段={len(bgm_segs)} onset={len(onsets)} 转场音效={len(transition_sfx)}处 -> {outp.name}",
          file=sys.stderr)
    print(f"     BGM段落: {bgm_segs[:8]}{'…' if len(bgm_segs)>8 else ''}", file=sys.stderr)
    print(f"     转场音效@切点: {transition_sfx[:12]}", file=sys.stderr)


if __name__ == "__main__":
    main()
