"""JSON-lines bridge to the pinned F2 Douyin profile paginator."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path


def cookie_header(path: Path | None) -> str:
    if path is None: return ""
    pairs=[]
    for raw in path.read_text(encoding="utf-8-sig",errors="replace").splitlines():
        line=raw.strip()
        if not line or (line.startswith("#") and not line.startswith("#HttpOnly_")): continue
        columns=line.split("\t")
        if len(columns)>=7: pairs.append(f"{columns[-2]}={columns[-1]}")
    if pairs: return "; ".join(pairs)
    return path.read_text(encoding="utf-8-sig",errors="replace").strip()


async def run(args):
    from f2.apps.douyin.handler import DouyinHandler
    from f2.apps.douyin.utils import ClientConfManager, SecUserIdFetcher

    kwargs={"cookie":cookie_header(args.cookies),"headers":{"User-Agent":ClientConfManager.user_agent(),"Referer":ClientConfManager.referer()},"proxies":ClientConfManager.proxies()}
    sec_user_id=await SecUserIdFetcher.get_sec_user_id(args.url); handler=DouyinHandler(kwargs)
    maximum=args.max_items or None
    async for page in handler.fetch_user_post_videos(sec_user_id=sec_user_id,max_cursor=int(args.cursor or 0),page_counts=min(20,args.max_items or 20),max_counts=maximum):
        raw=page._to_raw(); awemes=raw.get("aweme_list") or []; items=[]
        for row in awemes:
            identity=str(row.get("aweme_id") or "")
            if not identity: continue
            items.append({"id":identity,"url":f"https://www.douyin.com/video/{identity}","title":str(row.get("desc") or identity),"publishedAt":int(row.get("create_time") or 0) or None})
        author=(awemes[0].get("author") or {}) if awemes else {}
        print(json.dumps({"kind":"page","creatorId":sec_user_id,"creatorName":author.get("nickname"),"items":items,"nextCursor":str(raw.get("max_cursor")) if raw.get("has_more") else None,"hasMore":bool(raw.get("has_more"))},ensure_ascii=False),flush=True)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("url",nargs="?"); parser.add_argument("--max-items",type=int,default=0); parser.add_argument("--cursor",default=""); parser.add_argument("--cookies",type=Path); parser.add_argument("--doctor",action="store_true")
    args=parser.parse_args()
    if args.doctor:
        from f2.apps.douyin.handler import DouyinHandler  # noqa: F401
        from f2.apps.douyin.utils import ClientConfManager, SecUserIdFetcher  # noqa: F401
        print(json.dumps({"ready":True,"adapter":"f2-douyin-profile@0.0.1.7"})); return
    if not args.url: parser.error("url is required")
    asyncio.run(run(args))


if __name__=="__main__": main()
