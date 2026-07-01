#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""引擎注册表 —— 名字 -> 引擎类。上层只认名字，不认实现。"""
from .engines import QwenEngine, SoVITSEngine, TTSEngine

_REGISTRY = {
    "qwen": QwenEngine,
    "qwen3-tts": QwenEngine,
    "qwen3": QwenEngine,
    "gpt-sovits": SoVITSEngine,
    "sovits": SoVITSEngine,
}


def list_engines() -> list:
    return sorted(set(cls.name for cls in _REGISTRY.values()))


def get_engine(name: str = "qwen", device: str = "cpu", **kwargs) -> TTSEngine:
    key = (name or "qwen").lower()
    if key not in _REGISTRY:
        raise ValueError(f"未知引擎 '{name}'，可选: {list(_REGISTRY)}")
    return _REGISTRY[key](device=device, **kwargs)
