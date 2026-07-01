#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Qwen3-TTS 引擎适配器。

包两个模型：
  CustomVoice (9 预设音色)  -> synth_preset
  Base       (跨语言克隆)   -> synth_clone
两个都按需懒加载、各加载一次后常驻（CPU 单次加载 ~25s，server 模式只付一次）。

XPU 坑：Qwen3-TTS 0.1.1 在 Intel Arc XPU 上 generate 阶段 device 不一致，
故 device="xpu" 时强制降 CPU（见 HANDOFF §5.1）。
"""
import sys
from pathlib import Path
from typing import Optional

from .base import TTSEngine
from ..langmap import norm_lang, norm_speaker

ROOT = Path(__file__).resolve().parents[2]
CUSTOM_MODEL = ROOT / "models" / "Qwen3-TTS-12Hz-0.6B-CustomVoice"
BASE_MODEL = ROOT / "models" / "Qwen3-TTS-12Hz-0.6B-Base"

SPEAKERS = [
    {"id": "Vivian", "lang": "Chinese", "desc": "Bright edgy young female ⭐主声"},
    {"id": "Serena", "lang": "Chinese", "desc": "Warm gentle young female"},
    {"id": "Uncle_Fu", "lang": "Chinese", "desc": "Seasoned low male"},
    {"id": "Dylan", "lang": "Chinese", "desc": "Beijing male"},
    {"id": "Eric", "lang": "Chinese", "desc": "Sichuan male"},
    {"id": "Ryan", "lang": "English", "desc": "Dynamic English male"},
    {"id": "Aiden", "lang": "English", "desc": "Sunny American male"},
    {"id": "Ono_Anna", "lang": "Japanese", "desc": "Playful JP female ⭐纳西妲替代"},
    {"id": "Sohee", "lang": "Korean", "desc": "Warm Korean female"},
]


class QwenEngine(TTSEngine):
    name = "qwen"

    def __init__(self, device: str = "cpu",
                 custom_model: Optional[str] = None,
                 base_model: Optional[str] = None, **kw):
        super().__init__(device=device, **kw)
        self.custom_path = Path(custom_model) if custom_model else CUSTOM_MODEL
        self.base_path = Path(base_model) if base_model else BASE_MODEL
        self._custom = None
        self._base = None
        self._dtype = None

    # ---- 设备 ----
    def _resolve(self):
        import torch
        dev = self.device
        if dev == "xpu":
            print("[warn] Qwen3-TTS 0.1.1 在 XPU 上 generate 有 device bug，强制 CPU",
                  file=sys.stderr)
            dev = "cpu"
        elif dev == "cuda" and not torch.cuda.is_available():
            dev = "cpu"
        self.device = dev
        self._dtype = torch.float32 if dev == "cpu" else torch.bfloat16
        return dev, self._dtype

    def load(self) -> None:
        # 预热 CustomVoice（最常用）。Base 等首次 clone 再加载，省内存。
        self._ensure_custom()
        self._loaded = True

    def _new_model(self, path: Path):
        from qwen_tts import Qwen3TTSModel
        if not path.exists():
            raise FileNotFoundError(
                f"模型不存在: {path}\n  下: python -m modelscope download "
                f"--model Qwen/{path.name} --local_dir {path}")
        dev, dtype = self._resolve()
        print(f"[info] 加载 {path.name} (device={dev}) … 约 25s", file=sys.stderr)
        return Qwen3TTSModel.from_pretrained(str(path), device_map=dev, dtype=dtype)

    def _ensure_custom(self):
        if self._custom is None:
            self._custom = self._new_model(self.custom_path)
        return self._custom

    def _ensure_base(self):
        if self._base is None:
            self._base = self._new_model(self.base_path)
        return self._base

    # ---- 能力 ----
    def capabilities(self) -> set:
        return {"preset", "clone"}

    def list_speakers(self) -> list:
        return SPEAKERS

    # ---- 合成 ----
    def synth_preset(self, text, language, speaker, instruct=""):
        model = self._ensure_custom()
        wavs, sr = model.generate_custom_voice(
            text=text, language=norm_lang(language),
            speaker=norm_speaker(speaker), instruct=instruct or "")
        return wavs[0], sr

    def synth_clone(self, text, language, ref_audio, ref_text, ref_lang=None):
        model = self._ensure_base()
        wavs, sr = model.generate_voice_clone(
            text=text, language=norm_lang(language),
            ref_audio=str(ref_audio), ref_text=ref_text)
        return wavs[0], sr
