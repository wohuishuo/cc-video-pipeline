"""挑 ref_audio 候选
- 时长 3-15s
- 采样率 16kHz 或 24kHz
- 按文件大小排 (大文件=长且信息丰富, 但太大可能带背景音)
"""
import soundfile as sf
from pathlib import Path
import sys
import json

CHAR = sys.argv[1] if len(sys.argv) > 1 else "纳西妲"
ready = Path(rf"C:\Users\艾莉\Videos\cc视频剪辑\tools\tts-mvp\voices\{CHAR}_zh\ready")

results = []
for wav in sorted(ready.glob("*.wav")):
    try:
        info = sf.info(wav)
        dur = info.frames / info.samplerate
        if 3.0 <= dur <= 15.0 and info.samplerate in (16000, 22050, 24000, 32000, 44100, 48000):
            results.append({
                "name": wav.name,
                "sr": info.samplerate,
                "dur": dur,
                "ch": info.channels,
                "size_kb": wav.stat().st_size // 1024,
            })
    except Exception as e:
        pass

# 按时长 + 采样率打分
def score(r):
    # 24kHz 最对口 qwen3-tts
    sr_score = 100 if r["sr"] == 24000 else (50 if r["sr"] in (16000, 22050) else 20)
    # 时长 5-10s 最佳
    d = r["dur"]
    dur_score = 100 if 5 <= d <= 10 else (80 if 3 <= d <= 15 else 30)
    return sr_score + dur_score

results.sort(key=score, reverse=True)

print(f"=== {CHAR} 候选 (按得分排序) ===")
for r in results[:20]:
    print(f"  [{r['sr']:>5}Hz {r['dur']:5.1f}s {r['size_kb']:>5}KB ch={r['ch']}] {r['name'][:80]}")
