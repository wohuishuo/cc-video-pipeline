#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tts.py — Qwen3-TTS 配音工具 (CustomVoice)

用法:
  python tts.py --text "你好世界" --lang Chinese --speaker Vivian --out out.wav
  python tts.py --text "こんにちは" --lang Japanese --speaker Ono_Anna --out jp.wav
  python tts.py --text "Hello" --lang English --speaker Ryan --out en.wav

预设音色 (来自 Qwen3-TTS-12Hz-0.6B-CustomVoice):
  Vivian      中文    Bright, slightly edgy young female voice
  Serena      中文    Warm, gentle young female voice
  Uncle_Fu    中文    Seasoned male, low mellow
  Dylan       中文    Beijing 男声
  Eric        中文    Sichuan 男声
  Ryan        英文    Dynamic male, strong rhythmic
  Aiden       英文    Sunny American male
  Ono_Anna    日语    Playful Japanese female, light nimble  ← 纳西妲替代
  Sohee       韩语    Warm Korean female

支持语种 (10): Chinese, English, Japanese, Korean, German, French,
              Russian, Portuguese, Spanish, Italian

依赖: tools/tts-mvp/.venv (torch+xpu, qwen-tts, soundfile)
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "models" / "Qwen3-TTS-12Hz-0.6B-CustomVoice"
DEFAULT_OUT = ROOT / "outputs" / "out.wav"

# 把 --lang 标准化成 qwen-tts 期望的值
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

# 按用户常用场景定 short alias
SPEAKER_ALIAS = {
    "vivian": "Vivian", "serena": "Serena", "uncle": "Uncle_Fu",
    "dylan": "Dylan", "eric": "Eric", "ryan": "Ryan", "aiden": "Aiden",
    "anna": "Ono_Anna", "ono_anna": "Ono_Anna", "ono": "Ono_Anna",
    "nahida": "Ono_Anna",  # 别名: Cos 纳西妲场景
    "sohee": "Sohee",
}


def main() -> int:
    p = argparse.ArgumentParser(
        description="Qwen3-TTS 配音工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--text", required=True, help="要合成的文本")
    p.add_argument("--lang", default="Chinese",
                   help="语言 (Chinese/Japanese/English/Russian... 或 zh/jp/en/ru)")
    p.add_argument("--speaker", default="Vivian",
                   help="预设音色 (Vivian/Serena/Ono_Anna/Ryan... 简写 vivian/anna/ryan)")
    p.add_argument("--instruct", default="",
                   help="情感/语气指令 (e.g. '用特别愤怒的语气说')")
    p.add_argument("--out", default=str(DEFAULT_OUT), help="输出 wav 路径")
    p.add_argument("--device", default="xpu", choices=["xpu", "cpu", "cuda"],
                   help="推理设备 (默认 xpu)")
    p.add_argument("--model", default=str(MODEL_DIR),
                   help="模型本地路径 (默认 tools/tts-mvp/models/Qwen3-TTS-12Hz-0.6B-CustomVoice)")
    args = p.parse_args()

    # 标准化参数
    lang = LANG_ALIAS.get(args.lang.lower(), args.lang)
    speaker = SPEAKER_ALIAS.get(args.speaker.lower(), args.speaker)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 选 device / dtype
    import torch
    if args.device == "xpu":
        # XPU 当前在 Qwen3-TTS 0.1.1 内部 tensor device 不一致，先强制 CPU
        # 等官方 transformers + xpu 修这个 bug 再切回去
        print("[warn] Qwen3-TTS 0.1.1 在 Intel Arc XPU 上 generate 阶段有 device 不一致 bug,"
              " 暂时强制 CPU（待 transformers 修复后可改回 xpu）", file=sys.stderr)
        device = "cpu"
        dtype = torch.float32
    elif args.device == "cuda" and not torch.cuda.is_available():
        print("[warn] torch.cuda 不可用，退回 CPU", file=sys.stderr)
        device = "cpu"
        dtype = torch.float32
    else:
        device = args.device
        dtype = torch.float32 if device == "cpu" else torch.bfloat16

    # 延迟 import（重型库）
    from qwen_tts import Qwen3TTSModel
    import soundfile as sf

    model_path = Path(args.model)
    if not model_path.exists():
        print(f"[error] 模型目录不存在: {model_path}", file=sys.stderr)
        print("  跑: python -m modelscope download --model Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice "
              f"--local_dir {model_path}", file=sys.stderr)
        return 1

    print(f"[info] 加载模型: {model_path} (device={device}, dtype={dtype})")
    # 注: 直接 device_map="xpu" 会在 transformers mem_get_info 阶段 crash
    # （Intel Arc XPU 不支持 mem_get_info）。CPU 加载+显式搬移也不稳
    # （Qwen3-TTS 内部 tensor device 不一致）。稳定路径：device_map=目标。
    model = Qwen3TTSModel.from_pretrained(
        str(model_path),
        device_map=device,
        dtype=dtype,
    )

    print(f"[info] 合成: lang={lang} speaker={speaker} 文本={args.text[:50]}...")
    wavs, sr = model.generate_custom_voice(
        text=args.text,
        language=lang,
        speaker=speaker,
        instruct=args.instruct,
    )

    sf.write(str(out_path), wavs[0], sr)
    duration = len(wavs[0]) / sr
    print(f"[ok] 已写入: {out_path}  ({duration:.1f}s @ {sr}Hz)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
