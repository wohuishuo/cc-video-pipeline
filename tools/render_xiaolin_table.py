#!/usr/bin/env python
"""小Lin说 视频数据归一化 + 渲染 markdown 表格。

输出可读的全量视频表，按播放量降序。带分类标签便于选参考对象。
"""
import json, sys, re, html
from pathlib import Path

VIDEO_FILE = Path(__file__).resolve().parent.parent / "data" / "小Lin说" / "videos.json"
OUT_FILE = VIDEO_FILE.parent / "videos_table.md"

# 简易关键词分类（用于"哪类适合我参考"）
KEYWORD_MAP = {
    "人物/故事型": ["乔布斯","马斯克","巴菲特","LTCM","首富","赌神","之王", "林俊杰","张", "中国首富"],
    "企业/商业史": ["SpaceX", "苹果","OpenAI","ChatGPT","英伟达","AMD","特斯拉","沃尔沃","亚马逊","Meta","腾讯","阿里巴巴","微软","华为","字节","美团","拼多多","小米","OPPO","vivo","三星"],
    "金融/经济原理": ["金融危机","GDP","货币","利率","汇率","期货","黄金","债务","国债","OPEC","降息","加","美元","外汇","债务","基金","股市","理财","股票","房产","房价","买房","金本","私募","投资","资本","印钞"],
    "时事/政策": ["数据局","国务院","阅读促进条例","2034","2035","十四五","十五五","公务员","编制"],
    "体育/赛事": ["奥运","亚运","世界杯","夺冠","金牌","奖牌"],
    "生活方式": ["冰箱","洗衣机","手机","扫拖","笔记本","购车","汽车","飞机","高铁"],
    "AI/科技": ["AI", "人工智能", "模型", "大模型", "机器人", "算力", "芯片", "光刻机", "光刻", "英伟达", "AMD", "X-LKs", "ChatGPT", "Grok"],
    "国家/地缘": ["日本","德国","法国","印度","越南","韩国","朝鲜","乌克兰","俄罗斯","美国", "日本财团", "中东", "以色列"],
}

def category(title: str) -> str:
    for cat, kws in KEYWORD_MAP.items():
        for kw in kws:
            if kw in title:
                return cat
    return "其他/未分类"

def parse_length(l: str) -> int:
    """mm:ss 或 h:mm:ss → 秒；非数字/格式异常返回 0"""
    parts = l.split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except (ValueError, TypeError):
        return 0
    return 0

def is_short(l: str, max_min=10) -> bool:
    return parse_length(l) <= max_min * 60

def main():
    data = json.loads(VIDEO_FILE.read_text(encoding="utf-8"))
    videos = data.get("videos", [])

    # 计算时长+分类
    rows = []
    for v in videos:
        # 解码全部 HTML 实体（&amp; &lt; &gt; &nbsp; &#xxx; 等）
        title = html.unescape(v.get("title", ""))
        length = v.get("length", "")
        rows.append({
            "bvid": v.get("bvid", ""),
            "title": title,
            "length": length,
            "seconds": parse_length(length),
            "play": v.get("play", 0),
            "danmu": v.get("video_review", 0),
            "category": category(title),
            "short": is_short(length, max_min=10),
        })

    # 按播放降序
    rows.sort(key=lambda r: (-r["play"]))

    # 渲染 markdown 表
    out = [
        f"# 小Lin说 全部视频表（{data['total']} 条，按播放降序）",
        "",
        f"UP主: {data.get('up_name', '小Lin说')} | UID: {data.get('mid')} | 数据来源: {data.get('source')}",
        "",
        "## 全量表（按播放）",
        "",
        "| # | BV号 | 时长 | ≤10min? | 播放(万) | 弹幕 | 分类 | 标题 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(rows, 1):
        short = "✅" if r["short"] else ""
        out.append(f"| {i} | {r['bvid']} | {r['length']} | {short} | {r['play']:,} | {r['danmu']:,} | {r['category']} | {r['title']} |")

    # ≤10 分钟的 Top 30
    short_rows = [r for r in rows if r["short"]]
    out.extend([
        "",
        f"## 长度 ≤10 分钟 的视频（共 {len(short_rows)} 条，按播放降序）",
        "",
        "适合做 P0 参考（10 分钟内能完整精读，且能体现 SOP 模式）：",
        "",
        "| # | BV号 | 时长 | 播放(万) | 弹幕 | 分类 | 标题 |",
        "|---|---|---|---|---|---|---|",
    ])
    for i, r in enumerate(short_rows[:30], 1):
        out.append(f"| {i} | {r['bvid']} | {r['length']} | {r['play']:,} | {r['danmu']:,} | {r['category']} | {r['title']} |")

    # 短片+高播放 = 候选参考
    candidate = [r for r in short_rows if r["play"] >= 200][:15]
    out.extend([
        "",
        f"## 短片 + 高播放 候选参考对象（前 15）",
        "",
        "长度 ≤10min + 播放 ≥200万——结构成熟、可直接当模板学",
        "",
        "| # | BV号 | 时长 | 播放(万) | 弹幕 | 分类 | 标题 |",
        "|---|---|---|---|---|---|---|",
    ])
    for i, r in enumerate(candidate, 1):
        out.append(f"| {i} | {r['bvid']} | {r['length']} | {r['play']:,} | {r['danmu']:,} | {r['category']} | {r['title']} |")

    OUT_FILE.write_text("\n".join(out), encoding="utf-8")
    print(f"[ok] → {OUT_FILE}")
    print(f"     {len(rows)} 视频，{len(short_rows)} 短片，{len(candidate)} 候选参考")

if __name__ == "__main__":
    main()
