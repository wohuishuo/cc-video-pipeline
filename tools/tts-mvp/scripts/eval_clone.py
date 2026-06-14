"""eval_clone.py — 客观评估 VoiceClone 质量
对比 ref wav 和 clone wav:
  - F0 (基频) 走势
  - 时长 (压缩/拉伸)
  - 频谱包络 (MFCC 距离)
输出一个表格 + 一张图 (如果装了 matplotlib)
"""
import sys
import json
from pathlib import Path

def need(pkg):
    try:
        __import__(pkg)
        return True
    except ImportError:
        return False

def main():
    if len(sys.argv) < 3:
        print("用法: python eval_clone.py <ref.wav> <clone.wav>")
        sys.exit(1)
    ref = Path(sys.argv[1])
    clone = Path(sys.argv[2])
    if not ref.exists() or not clone.exists():
        print(f"[err] 文件不存在: {ref} 或 {clone}")
        sys.exit(1)

    import soundfile as sf
    import numpy as np

    ref_data, ref_sr = sf.read(str(ref))
    clone_data, clone_sr = sf.read(str(clone))
    # 单声道
    if ref_data.ndim > 1: ref_data = ref_data.mean(axis=1)
    if clone_data.ndim > 1: clone_data = clone_data.mean(axis=1)

    print(f"=== 客观评估 ===")
    print(f"ref:    {ref.name}  ({ref_sr}Hz, {len(ref_data)/ref_sr:.2f}s)")
    print(f"clone:  {clone.name}  ({clone_sr}Hz, {len(clone_data)/clone_sr:.2f}s)")

    # 1) 时长比
    dur_ref = len(ref_data) / ref_sr
    dur_clone = len(clone_data) / clone_sr
    rate = dur_clone / dur_ref
    print(f"\n时长: ref={dur_ref:.2f}s  clone={dur_clone:.2f}s  ratio={rate:.2f}x")

    # 2) RMS 能量
    rms_ref = float(np.sqrt(np.mean(ref_data**2)))
    rms_clone = float(np.sqrt(np.mean(clone_data**2)))
    print(f"RMS:  ref={rms_ref:.4f}  clone={rms_clone:.4f}  diff={abs(rms_ref-rms_clone)/max(rms_ref,1e-6)*100:.1f}%")

    # 3) F0 (基频) — 用 parselmouth/Praat
    if need("parselmouth"):
        import parselmouth
        from parselmouth.praat import call

        def get_f0(path, sr):
            snd = parselmouth.Sound(str(path), sampling_frequency=sr)
            pitch = call(snd, "To Pitch", 0.0, 75, 500)  # 75-500 Hz (人声范围)
            mean = call(pitch, "Get mean", 0, 0, "Hertz")
            return mean
        try:
            f0_ref = get_f0(ref, ref_sr)
            f0_clone = get_f0(clone, clone_sr)
            print(f"F0:   ref={f0_ref:.1f}Hz  clone={f0_clone:.1f}Hz  diff={abs(f0_ref-f0_clone):.1f}Hz")
        except Exception as e:
            print(f"F0: 失败 {e}")
    else:
        print("F0: 跳过 (parselmouth 未装)")

    # 4) 频谱包络 (MFCC 距离) — 需要 resample 到相同 sr
    if need("librosa"):
        import librosa
        # 重采样到 16kHz
        r1 = librosa.resample(ref_data.astype(float), orig_sr=ref_sr, target_sr=16000)
        r2 = librosa.resample(clone_data.astype(float), orig_sr=clone_sr, target_sr=16000)
        mfcc_ref = librosa.feature.mfcc(y=r1, sr=16000, n_mfcc=13)
        mfcc_clone = librosa.feature.mfcc(y=r2, sr=16000, n_mfcc=13)
        # DTW 对齐
        from librosa.sequence import dtw
        D, wp = dtw(X=mfcc_ref, Y=mfcc_clone, subseq=False, metric="euclidean")
        # 路径平均距离
        dtw_dist = D[-1, -1] / len(wp)
        print(f"MFCC-DTW 距离: {dtw_dist:.2f} (越小越像, 正常范围 30-80)")
    else:
        print("MFCC: 跳过 (librosa 未装)")

    # 5) 高频能量 (克隆常损失高频)
    if need("numpy"):
        import numpy as np
        def high_ratio(data, sr, cutoff=4000):
            from numpy.fft import rfft, rfftfreq
            spectrum = np.abs(rfft(data))
            freqs = rfftfreq(len(data), 1/sr)
            return float(spectrum[freqs > cutoff].sum() / spectrum.sum())
        hr_ref = high_ratio(ref_data, ref_sr)
        hr_clone = high_ratio(clone_data, clone_sr)
        print(f"高频占比 (>4kHz): ref={hr_ref*100:.1f}%  clone={hr_clone*100:.1f}%  loss={(1-hr_clone/hr_ref)*100:+.1f}%")

    print("\n=== 解读 ===")
    print("F0 差 < 30Hz: 音高接近")
    print("MFCC-DTW < 50: 音色接近 (理想 < 30)")
    print("高频损失 < 20%: 清晰度好")
    print("ratio 0.7-1.3: 时长合理")

if __name__ == "__main__":
    main()
