"""denoise_ref.py — 降噪参考音频"""
import sys
import noisereduce as nr
import soundfile as sf
import numpy as np
from pathlib import Path

if len(sys.argv) < 2:
    print("用法: python denoise_ref.py <wav> [out]")
    sys.exit(1)
src = Path(sys.argv[1])
dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_name(src.stem + "_denoised.wav")

data, sr = sf.read(str(src))
if data.ndim > 1:
    data = data.mean(axis=1)

# 用前 0.3s 估算噪声 (假设开头是纯噪声)
noise_clip = data[:int(sr * 0.3)]
reduced = nr.reduce_noise(y=data, sr=sr, y_noise=noise_clip, prop_decrease=0.7)

sf.write(str(dst), reduced, sr)
print(f"[ok] {src.name} → {dst.name}  ({len(data)/sr:.1f}s)")
