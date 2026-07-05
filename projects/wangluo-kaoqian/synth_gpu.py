# -*- coding: utf-8 -*-
"""XPU(Intel Arc) + torch.compile 加速版配音合成。

必须先满足：MSVC cl.exe 或 Intel oneAPI 在 PATH（inductor 编译 kernel 用）。
用 vcvars64.bat 激活后再跑本脚本。

与 synth.py 同样的分段/时间轴/跑飞保护逻辑，区别在：
  - 模型直接加载到 XPU 显存（bf16），不走 ttslib 的 force-cpu wrapper
  - torch.compile(talker, backend="inductor")
  - 首次预热若干次触发编译（~2.5min），之后稳态约 4-5x CPU
  - 每次生成前后 empty_cache，避免二次 OOM
"""
import json
import sys
import time
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
TTS_ROOT = ROOT.parent.parent / "tools" / "tts-mvp"
sys.path.insert(0, str(TTS_ROOT))  # 用生产里的原版 qwen_tts

import torch  # noqa: E402

# ── XPU mem_get_info 保护壳（Arc 130T 驱动不支持查显存）──
if hasattr(torch, "xpu") and torch.xpu.is_available():
    _GB = 16 * 1024 ** 3
    _orig_mgi = torch.xpu.mem_get_info
    def _safe_mgi(device=None):
        try:
            return _orig_mgi(device)
        except Exception:
            return (_GB, _GB)
    torch.xpu.mem_get_info = _safe_mgi

from qwen_tts import Qwen3TTSModel  # noqa: E402

BASE_MODEL = TTS_ROOT / "models" / "Qwen3-TTS-12Hz-0.6B-Base"
REF_WAV = TTS_ROOT / "voices" / "纳西妲_zh" / "ready" / "vo_dialog_LLZAQ004_nahida_01.wav"
REF_TEXT = "这次太感谢你们了，请好好休息。累了可以去洗个澡上个厕所转换心情哦。"

GAP_SEG = 0.25
GAP_ENTRY = 0.6
MAX_RETRY = 3
MAX_NEW_TOKENS = 600   # ~50s 音频硬上限，封顶 TTS 跑飞(无限复读)
DEVICE = "xpu"
DTYPE = torch.bfloat16


def gen(model, text, lang):
    """统一的生成调用：full prefill(质量更好) + max_new_tokens 封顶。"""
    return model.generate_voice_clone(
        text=text, language=lang_full(lang),
        ref_audio=str(REF_WAV), ref_text=REF_TEXT,
        non_streaming_mode=True, max_new_tokens=MAX_NEW_TOKENS)


def expected_max_dur(text, lang):
    n = len(text)
    if lang == "en":
        return max(25.0, n * 0.14)
    return max(20.0, n * 0.45)


def build_segments(entry):
    segs = []
    if entry["question_en"]:
        segs.append(("en", entry["question_en"]))
    zh = []
    if entry["answer"]:
        zh.append(f"答案是 {entry['answer']}。")
    if entry["conclusion"]:
        zh.append(entry["conclusion"])
    if zh:
        segs.append(("zh", "".join(zh)))
    return segs


def cache_clean():
    if torch.xpu.is_available():
        torch.xpu.empty_cache()


def synth_seg(model, text, lang):
    cap = expected_max_dur(text, lang)
    best = None
    for attempt in range(MAX_RETRY):
        cache_clean()
        wavs, sr = gen(model, text, lang)
        cache_clean()
        wav = wavs[0]
        dur = len(wav) / sr
        if best is None or dur < best[2]:
            best = (wav, sr, dur)
        if dur <= cap:
            return wav, sr, False
        print(f"    [retry {attempt+1}] [{lang}] {dur:.0f}s>上限{cap:.0f}s 跑飞重采样", flush=True)
    return best[0], best[1], True


def lang_full(code):
    return {"en": "English", "zh": "Chinese"}.get(code, code)


def warmup(model):
    print("[warmup] 触发 inductor 编译，首次约 2-3 分钟…", flush=True)
    t0 = time.time()
    for i, (txt, lg) in enumerate([
        ("This is a warmup sentence for the compiler.", "en"),
        ("这是一句用来预热编译器的中文。", "zh"),
        ("Another warmup pass to stabilize kernels.", "en"),
    ]):
        torch.xpu.synchronize()
        s = time.time()
        gen(model, txt, lg)
        torch.xpu.synchronize()
        print(f"[warmup {i+1}] {time.time()-s:.1f}s", flush=True)
    print(f"[warmup] 完成 总{time.time()-t0:.1f}s", flush=True)


def synth_part(part, out_dir, model):
    import numpy as np
    import soundfile as sf
    out_dir.mkdir(parents=True, exist_ok=True)
    t = 0.0
    entry_timings, all_audio, sr_ref = [], [], None
    for entry in part["entries"]:
        segs = build_segments(entry)
        if not segs:
            continue
        e_start = t
        seg_t = []
        for lang, text in segs:
            wav, sr, runaway = synth_seg(model, text, lang)
            if runaway:
                print(f"[warn] {entry['id']} [{lang}] 仍超长取最短", file=sys.stderr)
            sr_ref = sr_ref or sr
            dur = len(wav) / sr
            seg_t.append({"lang": lang, "text": text, "start": round(t, 3), "end": round(t + dur, 3)})
            all_audio.append(wav)
            t += dur
            all_audio.append(np.zeros(int(GAP_SEG * sr), dtype=wav.dtype))
            t += GAP_SEG
        t += (GAP_ENTRY - GAP_SEG)
        all_audio.append(np.zeros(int((GAP_ENTRY - GAP_SEG) * sr_ref), dtype="float32"))
        entry_timings.append({
            "id": entry["id"], "title_en": entry["title_en"], "title_zh": entry["title_zh"],
            "question_en": entry["question_en"], "answer": entry["answer"],
            "conclusion": entry["conclusion"], "table": entry["table"],
            "start": round(e_start, 3), "end": round(t - GAP_ENTRY + GAP_SEG, 3), "segments": seg_t,
        })
        print(f"  [{entry['id']}] {t:.1f}s", flush=True)
    full = np.concatenate(all_audio) if all_audio else np.zeros(1, dtype="float32")
    sf.write(str(out_dir / "narration.wav"), full, sr_ref or 24000)
    timings = {"part_no": part["part_no"], "part_title": part["part_title"],
               "total": round(len(full) / (sr_ref or 24000), 3), "entries": entry_timings}
    (out_dir / "timings.json").write_text(json.dumps(timings, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] PART {part['part_no']} -> {out_dir/'narration.wav'} ({timings['total']:.1f}s)", flush=True)


def main():
    parts = json.loads((ROOT / "parts.json").read_text(encoding="utf-8"))
    only = sys.argv[1] if len(sys.argv) > 1 else None
    print(f"[env] torch={torch.__version__} xpu={torch.xpu.is_available()}", flush=True)
    model = Qwen3TTSModel.from_pretrained(str(BASE_MODEL), device_map=DEVICE, dtype=DTYPE)
    print(f"[load] device={DEVICE} dtype={DTYPE}", flush=True)
    try:
        model.model.talker = torch.compile(model.model.talker, backend="inductor")
        print("[compile] talker compiled (inductor)", flush=True)
    except Exception as e:
        print(f"[compile] FAILED, 退回eager: {e}", flush=True)
    warmup(model)
    for part in parts:
        if only and str(part["part_no"]) != only:
            continue
        print(f"=== PART {part['part_no']} {part['part_title']} ===", flush=True)
        synth_part(part, ROOT / f"part{part['part_no']}", model)


if __name__ == "__main__":
    main()
