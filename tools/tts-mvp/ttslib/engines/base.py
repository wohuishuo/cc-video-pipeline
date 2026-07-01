#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""TTS 引擎抽象基类 —— 所有引擎（Qwen3-TTS / GPT-SoVITS / …）实现这一套接口，
上层（CLI / HTTP server / dub.py）只认这套接口，换引擎不改上层。

合成统一返回 (wav: np.ndarray float32 单声道, sr: int)。
"""
from abc import ABC, abstractmethod
from typing import Optional


class TTSEngine(ABC):
    name: str = "base"

    def __init__(self, device: str = "cpu", **kwargs):
        self.device = device
        self._loaded = False

    # ---- 生命周期 ----
    @abstractmethod
    def load(self) -> None:
        """加载模型（重，~秒级）。HTTP server 启动时调一次后常驻，解决反复加载。"""

    @property
    def loaded(self) -> bool:
        return self._loaded

    # ---- 能力声明 ----
    def capabilities(self) -> set:
        """返回支持的合成方式子集：{"preset", "clone"}。"""
        return set()

    def list_speakers(self) -> list:
        """返回 [{"id","lang","desc"}]，给 /voices 用。无预设音色返回 []。"""
        return []

    # ---- 合成 ----
    def synth_preset(self, text: str, language: str, speaker: str,
                     instruct: str = ""):
        """预设音色合成 -> (np.ndarray, sr)。不支持就抛 NotImplementedError。"""
        raise NotImplementedError(f"{self.name} 不支持预设音色合成")

    def synth_clone(self, text: str, language: str, ref_audio: str,
                    ref_text: str, ref_lang: Optional[str] = None):
        """跨语言克隆合成 -> (np.ndarray, sr)。不支持就抛 NotImplementedError。"""
        raise NotImplementedError(f"{self.name} 不支持声音克隆")
