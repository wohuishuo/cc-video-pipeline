import asyncio, json, sys, time
from pathlib import Path
from bilibili_api import search, video, user

async def search_up_videos(mid: int, up_name: str, out_dir: str, max_pages: int = 10):
    """通过搜索API获取UP主视频列表（被风控时的替代方案）"""
    all_videos = []
    seen = set()
    pn = 1
    while pn <= max_pages:
        try:
            res = await search.search_by_type(
                up_name, search_type=search.SearchObjectType.VIDEO,
                page=pn, order_type=search.OrderVideo.PUBDATE
            )
        except Exception as e:
            print(f'  search err p{pn}: {e}', file=sys.stderr)
            break
        items = res.get('result', [])
        if not items:
            break
        for item in items:
            if item.get('mid') != mid:
                continue
            bvid = item.get('bvid', '')
            if bvid in seen:
                continue
            seen.add(bvid)
            all_videos.append({
                'bvid': bvid,
                'title': item.get('title', '').replace('<em class="keyword">', '').replace('</em>', ''),
                'play': item.get('play', 0),
                'video_review': item.get('video_review', 0),
                'length': item.get('duration', ''),
                'author': item.get('author', ''),
            })
        print(f'  第{pn}页  累计{len(all_videos)}条匹配', file=sys.stderr)
        if len(items) < 20:
            break
        pn += 1
        time.sleep(0.5)

    out = Path(out_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'up_name': up_name,
        'mid': mid,
        'total': len(all_videos),
        'source': 'search_api',
        'videos': all_videos,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n共计 {len(all_videos)} 条视频\n', file=sys.stderr)
    for i, v in enumerate(all_videos, 1):
        print(f'{i:>3}  {v["bvid"]:<14} {v["length"]:>6} {v["play"]:>10,}   {v["title"][:70]}', file=sys.stderr)

if __name__ == '__main__':
    mid = int(sys.argv[1]) if len(sys.argv) > 1 else 520819684
    name = sys.argv[2] if len(sys.argv) > 2 else '小Lin说'
    out_dir = sys.argv[3] if len(sys.argv) > 3 else 'data/小Lin说/videos.json'
    asyncio.run(search_up_videos(mid, name, out_dir))
