#!/usr/bin/env python
"""合成一段无版权音乐床（口播垫底用）。纯 numpy，无需联网/素材。

用法:
  python music_bed.py --duration 31 --mood dark --bpm 76 --out music.wav

mood: dark(暗黑电影感,小调+低鼓) / calm(平静pad) / bright(明亮)
不是流行歌，是"氛围床"——刻意低调，垫在配音下不抢。
"""
import argparse
import numpy as np
import wave


def sine(f, t, phase=0.0):
    return np.sin(2 * np.pi * f * t + phase)


def adsr(n, sr, a=0.01, d=0.1, s=0.7, r=0.1):
    env = np.ones(n) * s
    ai, di, ri = int(a * sr), int(d * sr), int(r * sr)
    if ai: env[:ai] = np.linspace(0, 1, ai)
    if di: env[ai:ai+di] = np.linspace(1, s, di)
    if ri: env[-ri:] = np.linspace(env[-ri], 0, ri)
    return env


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=float, default=31)
    ap.add_argument("--bpm", type=float, default=76)
    ap.add_argument("--mood", default="dark", choices=["dark", "calm", "bright"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--gain", type=float, default=0.5, help="整体响度(0-1)")
    args = ap.parse_args()

    sr = 44100
    n = int(args.duration * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(7)

    if args.mood == "bright":
        roots = [261.63, 329.63, 392.0]      # C E G
        sub = 130.81
    elif args.mood == "calm":
        roots = [220.0, 277.18, 329.63]      # A C# E
        sub = 110.0
    else:  # dark, A minor
        roots = [220.0, 261.63, 329.63]      # A C E
        sub = 55.0

    out = np.zeros(n)
    # 1) 低音 drone + sub：缓慢起伏
    swell = 0.5 + 0.5 * np.sin(2 * np.pi * 0.05 * t - np.pi/2)  # 20s 周期的缓慢呼吸
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5 * t)
    for f in roots:
        out += 0.12 * sine(f * vib, t) * swell
    out += 0.18 * sine(sub, t) * swell

    # 2) pad 和弦泛音（高八度，轻）
    for f in roots:
        out += 0.05 * sine(f * 2, t) * (0.4 + 0.6 * swell)

    # 3) 低鼓脉冲（每拍）
    beat = 60.0 / args.bpm
    klen = int(0.16 * sr)
    kt = np.arange(klen) / sr
    kick = np.sin(2 * np.pi * 58 * kt * (1 - kt / (0.16*2))) * np.exp(-kt * 22)
    b = beat
    while b < args.duration:
        i = int(b * sr)
        if i + klen < n:
            out[i:i+klen] += 0.5 * kick
        b += beat

    # 4) 高频微弱 shimmer（滤波噪声 + 慢颤）
    noise = rng.standard_normal(n)
    # 简单一阶高通
    hp = np.diff(noise, prepend=0)
    trem = 0.5 + 0.5 * np.sin(2 * np.pi * 0.15 * t)
    out += 0.015 * hp * trem

    # 5) 整体张力渐强（尾段抬一点）
    rise = np.linspace(0.85, 1.12, n)
    out *= rise

    # 归一化 + gain
    out = out / (np.max(np.abs(out)) + 1e-9) * args.gain
    # 头尾淡入淡出
    fade = int(0.8 * sr)
    out[:fade] *= np.linspace(0, 1, fade)
    out[-fade:] *= np.linspace(1, 0, fade)

    # 立体声：轻微左右去相关
    delay = int(0.012 * sr)
    right = np.concatenate([np.zeros(delay), out[:-delay]])
    stereo = np.stack([out, right], axis=1)
    pcm = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)

    with wave.open(args.out, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    print(f"[ok] 音乐床 {args.duration:.0f}s {args.mood} {args.bpm:.0f}bpm -> {args.out}")


if __name__ == "__main__":
    main()
