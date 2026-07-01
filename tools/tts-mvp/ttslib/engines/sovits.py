#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GPT-SoVITS 引擎适配器 —— 适配槽（接口已留好，推理未接入）。

为什么先留槽不接：D 盘那个纳西妲 so-vits 模型不完整（只有 G_22400.pth + config.json，
缺 hubert / content_encoder 等，无法直接推理，见 HANDOFF §5.8）。等拿到完整权重再接。

============ 接入步骤（给未来的自己/接手 AI）============
GPT-SoVITS 官方推理走它自带的 HTTP API（api.py / api_v2.py），最省事的接法是
"代理"：本引擎不在进程内跑模型，而是 POST 到 GPT-SoVITS 自己的服务。

1) 装官方仓库（独立 venv，别污染本 MVP）：
     git clone https://github.com/RVC-Boss/GPT-SoVITS
     # 按官方装依赖 + 下预训练底模（GPT_SoVITS/pretrained_models/）
2) 放角色权重：<exp>.ckpt (GPT) + <exp>.pth (SoVITS)，和参考音频 ref.wav + ref_text
3) 起官方服务：python api_v2.py -a 127.0.0.1 -p 9880
4) 把下面 _SOVITS_URL 指过去，填齐 synth_clone 的 POST body（官方 /tts 入参）
5) 在 registry 里它已注册名 "gpt-sovits"/"sovits"，server.py --engine sovits 即可切

GPT-SoVITS 的定位：**少样本声音克隆**（几秒~1分钟样本即可），中日英效果好，
适合做"卡夏本人声线"或角色声线的高保真克隆——比 Qwen 跨语言克隆音色更像，
但没有 Qwen 的"开箱即用预设音色"。两个引擎互补，所以做成可切换。
=========================================================
"""
from typing import Optional

from .base import TTSEngine

_SOVITS_URL = "http://127.0.0.1:9880"  # 官方 api_v2.py 默认；接入时改这里
_NOT_READY = (
    "GPT-SoVITS 适配槽已就位但未接入推理。\n"
    "原因：本地缺完整角色权重（HANDOFF §5.8）。\n"
    "接入步骤见 ttslib/engines/sovits.py 顶部 docstring。"
)


class SoVITSEngine(TTSEngine):
    name = "gpt-sovits"

    def __init__(self, device: str = "cpu", url: Optional[str] = None, **kw):
        super().__init__(device=device, **kw)
        self.url = url or _SOVITS_URL

    def load(self) -> None:
        raise NotImplementedError(_NOT_READY)

    def capabilities(self) -> set:
        # 接入后改成 {"clone"}（GPT-SoVITS 主打少样本克隆，无固定预设音色）
        return set()

    def synth_clone(self, text, language, ref_audio, ref_text, ref_lang=None):
        # 接入示例（取消注释 + 按官方 api_v2 入参补全）：
        #   import requests, soundfile as sf, io
        #   r = requests.post(f"{self.url}/tts", json={
        #       "text": text, "text_lang": _lang2code(language),
        #       "ref_audio_path": str(ref_audio), "prompt_text": ref_text,
        #       "prompt_lang": _lang2code(ref_lang or language),
        #       "media_type": "wav"})
        #   r.raise_for_status()
        #   wav, sr = sf.read(io.BytesIO(r.content))
        #   return wav, sr
        raise NotImplementedError(_NOT_READY)
