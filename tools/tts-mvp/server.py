#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""TTS HTTP 服务 —— 别的项目用这个调，不用共享 venv、不用每次加载模型。

起服务（模型常驻，启动加载一次）:
  .\.venv\Scripts\python.exe server.py                 # 默认 qwen, 127.0.0.1:8757
  .\.venv\Scripts\python.exe server.py --engine qwen --port 8757
  .\.venv\Scripts\python.exe server.py --no-preload    # 不预热, 首次请求再加载

接口:
  GET  /health                 -> {status, engine, device, loaded, capabilities}
  GET  /voices                 -> [{id, lang, desc}]
  POST /tts    {text, lang, speaker?, instruct?}                 -> audio/wav
  POST /clone  {text, lang, ref_audio, ref_text, ref_lang?}      -> audio/wav
       两者都支持 ?save=<绝对路径> 把 wav 落盘并返回 {path, duration, sr}

别的项目调用示例见 client_example.py。

并发：模型推理串行（一把锁），本地单机 MVP 足够；要并发再上多 worker。
"""
import argparse
import io
import sys
import threading
from pathlib import Path

import numpy as np
import soundfile as sf
from fastapi import FastAPI, Query, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ttslib import get_engine  # noqa: E402

app = FastAPI(title="cc-tts-mvp", version="1.0")
_LOCK = threading.Lock()
_ENGINE = None
_CFG = {"engine": "qwen", "device": "cpu"}


def engine():
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = get_engine(_CFG["engine"], device=_CFG["device"])
    return _ENGINE


def _wav_bytes(wav: np.ndarray, sr: int) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, wav, sr, format="WAV")
    return buf.getvalue()


def _respond(wav, sr, save):
    if save:
        p = Path(save)
        p.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(p), wav, sr)
        return JSONResponse({"path": str(p), "duration": round(len(wav) / sr, 3), "sr": sr})
    return Response(content=_wav_bytes(wav, sr), media_type="audio/wav")


class TTSReq(BaseModel):
    text: str
    lang: str = "zh"
    speaker: str = "Vivian"
    instruct: str = ""


class CloneReq(BaseModel):
    text: str
    lang: str
    ref_audio: str
    ref_text: str
    ref_lang: str = "auto"


@app.get("/health")
def health():
    e = _ENGINE
    return {
        "status": "ok",
        "engine": _CFG["engine"],
        "device": _CFG["device"],
        "loaded": bool(e and e.loaded),
        "capabilities": sorted(e.capabilities()) if e else [],
    }


@app.get("/voices")
def voices():
    return engine().list_speakers()


@app.post("/tts")
def tts(req: TTSReq, save: str = Query(default="")):
    with _LOCK:
        wav, sr = engine().synth_preset(req.text, req.lang, req.speaker, req.instruct)
    return _respond(wav, sr, save)


@app.post("/clone")
def clone(req: CloneReq, save: str = Query(default="")):
    ref_lang = None if req.ref_lang == "auto" else req.ref_lang
    with _LOCK:
        wav, sr = engine().synth_clone(req.text, req.lang, req.ref_audio,
                                       req.ref_text, ref_lang)
    return _respond(wav, sr, save)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="qwen")
    ap.add_argument("--device", default="cpu", choices=["cpu", "xpu", "cuda"])
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8757)
    ap.add_argument("--no-preload", action="store_true", help="不在启动时加载模型")
    args = ap.parse_args()
    _CFG["engine"] = args.engine
    _CFG["device"] = args.device

    if not args.no_preload:
        print(f"[*] 预热引擎 {args.engine} (device={args.device}) …", file=sys.stderr)
        try:
            engine().load()
            print("[ok] 模型已常驻，请求不再重复加载", file=sys.stderr)
        except NotImplementedError as e:
            print(f"[warn] {e}", file=sys.stderr)

    import uvicorn
    print(f"[*] TTS 服务 http://{args.host}:{args.port}  (POST /tts, /clone)", file=sys.stderr)
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
