#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""语种 / 音色别名归一化 —— 全 MVP 共用一份，避免各脚本各写一份漂移。"""

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

# 预设音色简写（Qwen3-TTS CustomVoice）
SPEAKER_ALIAS = {
    "vivian": "Vivian", "serena": "Serena", "uncle": "Uncle_Fu",
    "dylan": "Dylan", "eric": "Eric", "ryan": "Ryan", "aiden": "Aiden",
    "anna": "Ono_Anna", "ono_anna": "Ono_Anna", "ono": "Ono_Anna",
    "nahida": "Ono_Anna", "sohee": "Sohee",
}


def norm_lang(s: str) -> str:
    return LANG_ALIAS.get((s or "").lower(), s)


def norm_speaker(s: str) -> str:
    return SPEAKER_ALIAS.get((s or "").lower(), s)
