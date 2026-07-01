#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ttslib —— 可复用的本地 TTS 核心。

给别的项目用最简单的两条路：
  1) 进程内（同 venv）:   from ttslib import get_engine
  2) 跨项目/跨语言:        起 server.py，POST http://127.0.0.1:8757/tts

引擎可插拔（qwen / gpt-sovits），上层只认 get_engine 与 HTTP 接口。
"""
from .registry import get_engine, list_engines
from .engines import TTSEngine
from . import align, langmap

__all__ = ["get_engine", "list_engines", "TTSEngine", "align", "langmap"]
