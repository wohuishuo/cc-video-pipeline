#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
cross_clone.py — Qwen3-TTS 跨语言 VoiceClone

用法:
  python cross_clone.py --ref voices/nahida_jp/raw/xxx.wav --ref_text "草神です" \
                        --text "Привет мир" --lang Russian --out voices/clone_ru.wav

要求:
  - 已下载 Qwen3-TTS-12Hz-0.6B-Base 模型 (Base 不是 CustomVoice, 才有 VoiceClone)
  - 参考音频 wav, 24kHz 最好, 3-30 秒最佳
  - ref_text: 参考音频的文本 (与 --lang 一致, 必须真实)

执行流程:
  1. 加载 Qwen3-TTS-12Hz-0.6B-Base
  2. 用 ref_audio + ref_text 编码说话人嵌入
  3. 用 text + lang + 说话人嵌入生成新语音

性能: CPU 模式比 CustomVoice 慢 1.5-2x (多一次 encode)
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE_MODEL = ROOT / "models" / "Qwen3-TTS-12Hz-0.6B-Base"
DEFAULT_OUT = ROOT / "outputs" / "cloned.wav"

LANG_ALIAS = {
    "zh": "Chinese", "cn": "Chinese", "chinese": "Chinese",
    "en": "English", "english": "English",
    "jp": "Japanese", "ja": "Japanese", "japanese": "Japanese",
    "ko": "Korean", "korean": "Korean",
    "ru": "Russian", "russian": "Russian",
    "de": "German", "german": "German",
    "fr": "French", "french": "French",
    "pt": "Portuguese", "portuguese": "Portuguese",
    "es": "Spanish", "spanish": "Spanish",
    "it": "Italian", "italian": "Italian",
}


def main() -> int:
    p = argparse.ArgumentParser(
        description="Qwen3-TTS 跨语言 VoiceClone",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--ref", required=True, help="参考音频 wav 路径 (3-30s 干净语音)")
    p.add_argument("--ref_text", required=True, help="参考音频的文本 (必须与实际发音一致)")
    p.add_argument("--ref_lang", default="auto",
                   help="参考音频语种 (默认 auto; 一般 = --lang 但不强制)")
    p.add_argument("--text", required=True, help="要合成的目标文本")
    p.add_argument("--lang", required=True, help="目标语种 (zh/jp/en/ru/...)")
    p.add_argument("--out", default=str(DEFAULT_OUT), help="输出 wav 路径")
    p.add_argument("--device", default="cpu", choices=["xpu", "cpu", "cuda"],
                   help="推理设备 (默认 cpu)")
    p.add_argument("--model", default=str(BASE_MODEL),
                   help="Base 模型本地路径")
    args = p.parse_args()

    ref_path = Path(args.ref)
    if not ref_path.exists():
        print(f"[error] 参考音频不存在: {ref_path}", file=sys.stderr)
        return 1
    model_path = Path(args.model)
    if not model_path.exists():
        print(f"[error] Base 模型目录不存在: {model_path}", file=sys.stderr)
        print("  下: python -m modelscope download --model Qwen/Qwen3-TTS-12Hz-0.6B-Base "
              f"--local_dir {model_path}", file=sys.stderr)
        return 1
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    target_lang = LANG_ALIAS.get(args.lang.lower(), args.lang)
    ref_lang = (LANG_ALIAS.get(args.ref_lang.lower(), args.ref_lang)
                if args.ref_lang != "auto" else target_lang)

    import torch
    device = args.device
    if device == "xpu" and not torch.xpu.is_available():
        device = "cpu"
    dtype = torch.float32 if device == "cpu" else torch.bfloat16

    from qwen_tts import Qwen3TTSModel
    import soundfile as sf

    print(f"[info] 加载 Base 模型: {model_path} (device={device})")
    model = Qwen3TTSModel.from_pretrained(
        str(model_path),
        device_map=device,
        dtype=dtype,
    )

    print(f"[info] 跨语言 VoiceClone:")
    print(f"  ref:    {ref_path.name} ({ref_lang}): {args.ref_text[:50]}")
    print(f"  target: ({target_lang}): {args.text[:50]}")
    wavs, sr = model.generate_voice_clone(
        text=args.text,
        language=target_lang,
        ref_audio=str(ref_path),
        ref_text=args.ref_text,
    )
    sf.write(str(out_path), wavs[0], sr)
    dur = len(wavs[0]) / sr
    print(f"[ok] {out_path}  ({dur:.1f}s @ {sr}Hz)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
