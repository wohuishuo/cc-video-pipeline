#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""parts.json -> 每个 Part 一条配音(纳西妲克隆声线，英文题干/中文结论切换) + 时间轴。

输出 partN/narration.wav + partN/timings.json（驱动 Remotion 卡片动画的时间轴）。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TTS_ROOT = ROOT.parent.parent / "tools" / "tts-mvp"
sys.path.insert(0, str(TTS_ROOT))
from ttslib import get_engine  # noqa: E402

REF_WAV = TTS_ROOT / "voices" / "纳西妲_zh" / "ready" / "vo_dialog_LLZAQ004_nahida_01.wav"
REF_TEXT = "这次太感谢你们了，请好好休息。累了可以去洗个澡上个厕所转换心情哦。"

GAP_SEG = 0.25   # 同条目内 en->zh 段间隙
GAP_ENTRY = 0.6  # 条目之间的间隙
MAX_RETRY = 3    # TTS 偶尔会在数字/长句上跑飞(无限复读)，超长就重采样
MAX_NEW_TOKENS = 600  # ~50s 音频硬上限，封顶跑飞(否则单段能跑11分钟)


def gen(eng, text, lang):
    """直接调底层模型，带 max_new_tokens 硬封顶(engine.synth_clone 不转发kwargs)。"""
    model = eng._ensure_base()
    wavs, sr = model.generate_voice_clone(
        text=text, language=("English" if lang == "en" else "Chinese"),
        ref_audio=str(REF_WAV), ref_text=REF_TEXT,
        max_new_tokens=MAX_NEW_TOKENS)
    return wavs[0], sr


def expected_max_dur(text: str, lang: str) -> float:
    """这段文本正常顶多多长(秒)。超过就判定跑飞、重来。给足 1.8x 余量。"""
    n = len(text)
    if lang == "en":
        return max(25.0, n * 0.14)   # 英文 ~0.08s/字符
    return max(20.0, n * 0.45)        # 中文 ~0.25s/字


def synth_seg(eng, text: str, lang: str):
    """带跑飞重采样的单段合成，返回最短的一条干净音频。"""
    cap = expected_max_dur(text, lang)
    best = None
    for attempt in range(MAX_RETRY):
        wav, sr = gen(eng, text, lang)
        dur = len(wav) / sr
        if best is None or dur < best[2]:
            best = (wav, sr, dur)
        if dur <= cap:
            return wav, sr, attempt, False
        print(f"    [retry {attempt+1}] [{lang}] {dur:.0f}s > 上限{cap:.0f}s，疑似跑飞，重采样", flush=True)
    return best[0], best[1], MAX_RETRY, True  # 仍超长则用最短的一条


def build_segments(entry: dict) -> list:
    """一条题目 -> [(lang, text)]，英文题干 + 中文答案&结论。"""
    segs = []
    if entry["question_en"]:
        segs.append(("en", entry["question_en"]))
    zh_parts = []
    if entry["answer"]:
        zh_parts.append(f"答案是 {entry['answer']}。")
    if entry["conclusion"]:
        zh_parts.append(entry["conclusion"])
    if zh_parts:
        segs.append(("zh", "".join(zh_parts)))
    return segs


def synth_part(part: dict, out_dir: Path, eng) -> dict:
    import numpy as np
    import soundfile as sf

    out_dir.mkdir(parents=True, exist_ok=True)
    t = 0.0
    entry_timings = []
    all_audio = []
    sr_ref = None

    for entry in part["entries"]:
        segs = build_segments(entry)
        if not segs:
            continue
        e_start = t
        seg_timings = []
        for lang, text in segs:
            try:
                wav, sr, _att, _runaway = synth_seg(eng, text, lang)
                if _runaway:
                    print(f"[warn] {entry['id']} [{lang}] {MAX_RETRY}次仍超长，取最短", file=sys.stderr)
            except Exception as exc:
                print(f"[err] {entry['id']} [{lang}] 合成失败: {exc}", file=sys.stderr)
                continue
            sr_ref = sr_ref or sr
            dur = len(wav) / sr
            seg_timings.append({"lang": lang, "text": text, "start": round(t, 3), "end": round(t + dur, 3)})
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
            "start": round(e_start, 3), "end": round(t - GAP_ENTRY + GAP_SEG, 3),
            "segments": seg_timings,
        })
        print(f"  [{entry['id']}] {t:.1f}s 累计")

    wav_path = out_dir / "narration.wav"
    full = np.concatenate(all_audio) if all_audio else np.zeros(1, dtype="float32")
    sf.write(str(wav_path), full, sr_ref or 24000)
    timings = {
        "part_no": part["part_no"], "part_title": part["part_title"],
        "total": round(len(full) / (sr_ref or 24000), 3), "entries": entry_timings,
    }
    (out_dir / "timings.json").write_text(json.dumps(timings, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] PART {part['part_no']} -> {wav_path} ({timings['total']:.1f}s)")
    return timings


def main():
    parts = json.loads((ROOT / "parts.json").read_text(encoding="utf-8"))
    only = sys.argv[1] if len(sys.argv) > 1 else None
    eng = get_engine("qwen", device="cpu")
    eng.load()
    for part in parts:
        if only and str(part["part_no"]) != only:
            continue
        print(f"=== PART {part['part_no']} {part['part_title']} ({len(part['entries'])}题) ===")
        synth_part(part, ROOT / f"part{part['part_no']}", eng)


if __name__ == "__main__":
    main()
