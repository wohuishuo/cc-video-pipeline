#!/usr/bin/env python
"""B站视频数据抓取工具 —— 为 P3 数据复盘做准备。

功能：
    1. 根据 BV 号获取视频元数据（播放量、点赞、投币、收藏、弹幕、评论、分享）
    2. 获取视频弹幕
    3. 获取热门评论
    4. 获取 UP 主信息

用法：
    python bilibili_data.py bv <BV号>                    # 视频元数据
    python bilibili_data.py danmaku <BV号>                # 弹幕列表
    python bilibili_data.py comments <BV号>               # 热门评论
    python bilibili_data.py up <UID>                      # UP 主信息
    python bilibili_data.py search <关键词> [--count 20]   # 搜视频

输出：JSON 到 stdout，可直接 pipe 给 Claude 分析。

依赖：pip install bilibili-api-python
认证：如需高清/会员数据，需配 Cookie —— 设置环境变量 BILI_COOKIE_FILE 指向 cookies.txt
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

try:
    from bilibili_api import video, user, search, sync
except ImportError:
    print("[err] pip install bilibili-api-python", file=sys.stderr)
    raise


def _load_cookie():
    """从 cookies.txt（Netscape 格式）加载 cookie 字符串给 bilibili_api"""
    cookie_file = os.environ.get("BILI_COOKIE_FILE",
        str(Path(__file__).resolve().parent.parent / "reference" / "cookies.txt"))
    if not Path(cookie_file).exists():
        return None
    # bilibili_api 的 Credential 需要 SESSDATA / bili_jct / dedeuserid / buvid3
    with open(cookie_file, encoding="utf-8") as f:
        cookies = {}
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 7:
                cookies[parts[5]] = parts[6]
    sessdata = cookies.get("SESSDATA", "")
    bili_jct = cookies.get("bili_jct", "")
    dedeuserid = cookies.get("DedeUserID", "")
    buvid3 = cookies.get("buvid3", "")
    if not sessdata:
        return None
    from bilibili_api import Credential
    return Credential(sessdata=sessdata, bili_jct=bili_jct,
                      dedeuserid=dedeuserid, buvid3=buvid3)


async def get_video_info(bvid: str) -> dict:
    """获取视频详细信息"""
    v = video.Video(bvid=bvid, credential=_load_cookie())
    info = await v.get_info()
    stat = info.get("stat", {})
    return {
        "bvid": bvid,
        "title": info.get("title", ""),
        "desc": info.get("desc", ""),
        "duration": info.get("duration", 0),  # 秒
        "owner": {
            "name": info.get("owner", {}).get("name", ""),
            "mid": info.get("owner", {}).get("mid", 0),
            "face": info.get("owner", {}).get("face", ""),
        },
        "stat": {
            "view":  stat.get("view", 0),
            "danmaku": stat.get("danmaku", 0),
            "reply": stat.get("reply", 0),
            "favorite": stat.get("favorite", 0),
            "coin": stat.get("coin", 0),
            "share": stat.get("share", 0),
            "like": stat.get("like", 0),
        },
        "pubdate": info.get("pubdate", 0),
        "tname": info.get("tname", ""),   # 分区
        "tags": [t.get("tag_name", "") for t in (info.get("tags") or [])],
    }


async def get_danmaku(bvid: str, max_count: int = 200) -> list:
    """获取视频弹幕（按热度排序）"""
    v = video.Video(bvid=bvid, credential=_load_cookie())
    dms = []
    try:
        # bilibili_api 的 page_index 是 0-based（分 P 号从 0 开始）
        page = 0
        while len(dms) < max_count:
            d = await v.get_danmakus(page_index=page)
            if not d:
                break
            for dm in d:
                dms.append({
                    "time": round(dm.dm_time, 2) if hasattr(dm, 'dm_time') else 0,
                    "text": dm.text if hasattr(dm, 'text') else str(dm),
                    "mode": dm.mode if hasattr(dm, 'mode') else 0,
                })
            page += 1  # 下一页（多 P 视频）
            if page > 5:  # 最多取 5 页
                break
    except Exception as e:
        print(f"[warn] 弹幕获取失败: {e}", file=sys.stderr)
    return dms[:max_count]


async def get_comments(bvid: str, count: int = 20) -> list:
    """获取视频热门评论"""
    v = video.Video(bvid=bvid, credential=_load_cookie())
    comments = []
    try:
        page = 1
        while len(comments) < count:
            c = await v.get_comments(page_index=page, order="hot")
            if not c.get("replies"):
                break
            for r in c["replies"]:
                comments.append({
                    "user": r.get("member", {}).get("uname", ""),
                    "content": r.get("content", {}).get("message", ""),
                    "like": r.get("like", 0),
                    "replies": r.get("rcount", 0),
                })
            page += 1
            if page > 3:
                break
    except Exception as e:
        print(f"[warn] 评论获取失败: {e}", file=sys.stderr)
    return comments[:count]


async def get_user_info(mid: int) -> dict:
    """获取 UP 主信息"""
    u = user.User(uid=mid, credential=_load_cookie())
    info = await u.get_user_info()
    stat = await u.get_relation_info()
    return {
        "mid": mid,
        "name": info.get("name", ""),
        "sign": info.get("sign", ""),
        "level": info.get("level", 0),
        "follower": stat.get("follower", 0),
        "video_count": info.get("video_count", 0),
    }


async def search_videos(keyword: str, count: int = 20) -> list:
    """搜索 B站视频（按播放量排序）"""
    res = await search.search_by_type(keyword, search_type=search.SearchObjectType.VIDEO,
                                       page=1, order_type=search.OrderVideo.PLAY)
    items = res.get("result", [])[:count]
    videos = []
    for item in items:
        videos.append({
            "bvid": item.get("bvid", ""),
            "title": item.get("title", "").replace('<em class="keyword">', '').replace('</em>', ''),
            "author": item.get("author", ""),
            "play": item.get("play", 0),
            "danmaku": item.get("video_review", 0),
            "duration": item.get("duration", ""),
        })
    return videos


async def main():
    ap = argparse.ArgumentParser(description="B站视频数据抓取工具")
    ap.add_argument("action", choices=["bv","danmaku","comments","up","search"])
    ap.add_argument("target", help="BV号 / UID / 关键词")
    ap.add_argument("--count", type=int, default=20, help="数量（默认20）")
    ap.add_argument("--out", default=None, help="输出 JSON 文件路径")
    args = ap.parse_args()

    result = None
    if args.action == "bv":
        result = await get_video_info(args.target)
    elif args.action == "danmaku":
        result = await get_danmaku(args.target, args.count)
    elif args.action == "comments":
        result = await get_comments(args.target, args.count)
    elif args.action == "up":
        result = await get_user_info(int(args.target))
    elif args.action == "search":
        result = await search_videos(args.target, args.count)

    if args.out:
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
        print(f"[ok] -> {args.out}", file=sys.stderr)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
