#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""别的项目怎么调这个 TTS MVP —— 三种方式示例。

前提：另一个终端已起服务
  cd tools/tts-mvp; .\.venv\Scripts\python.exe server.py
"""
import sys
import urllib.request
import json

BASE = "http://127.0.0.1:8757"


def post(path, payload, save=None):
    url = f"{BASE}{path}" + (f"?save={save}" if save else "")
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        ctype = r.headers.get("Content-Type", "")
        body = r.read()
    return ctype, body


def main():
    # 1) 拿到 wav 字节，自己写文件（跨语言通用，curl 也一样）
    ctype, body = post("/tts", {"text": "你好，这是跨项目调用", "lang": "zh", "speaker": "vivian"})
    if ctype.startswith("audio"):
        open("from_other_project.wav", "wb").write(body)
        print(f"[ok] 收到 {len(body)} 字节 wav -> from_other_project.wav")

    # 2) 让服务端直接落盘（省传输，适合同机另一个项目）
    ctype, body = post("/tts",
                       {"text": "金字塔结构，结论先行", "lang": "zh", "speaker": "serena"},
                       save="C:/tmp/line2.wav")
    print("[ok] 落盘:", body.decode("utf-8"))

    # 3) 克隆（纳西妲声线说日语）—— 需要 ref_audio 路径
    # ctype, body = post("/clone", {
    #     "text": "草神です、よろしく", "lang": "ja",
    #     "ref_audio": "voices/纳西妲_zh/ready/vo_dialog_LLZAQ004_nahida_01.wav",
    #     "ref_text": "这次太感谢你们了，请好好休息。", "ref_lang": "zh"})


if __name__ == "__main__":
    sys.exit(main())
