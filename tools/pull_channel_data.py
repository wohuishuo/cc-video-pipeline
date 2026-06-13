import asyncio, json, sys
from pathlib import Path
from bilibili_api import user

async def pull_channel(uid: int, out_dir: str):
    u = user.User(uid=uid)
    info = await u.get_user_info()
    up_name = info.get('name', '?')
    follower = 0
    try:
        stat = await u.get_relation_info()
        follower = stat.get('follower', 0)
    except Exception:
        pass

    print(f'UP主: {up_name}  粉丝: {follower}', file=sys.stderr)

    all_videos = []
    pn = 1
    while pn <= 50:
        try:
            page = await u.get_videos(pn=pn, ps=50, order=user.VideoOrder.PUBDATE)
        except Exception as e:
            print(f'err p{pn}: {e}', file=sys.stderr)
            break
        vlist = page.get('list', {}).get('vlist', [])
        if not vlist:
            break
        for v in vlist:
            all_videos.append({
                'bvid': v.get('bvid', ''),
                'title': v.get('title', ''),
                'created': v.get('created', 0),
                'length': v.get('length', ''),
                'play': v.get('play', 0),
                'comment': v.get('comment', 0),
                'video_review': v.get('video_review', 0),
                'favorites': v.get('favorites', 0),
            })
        print(f'  第{pn}页  累计{len(all_videos)}条', file=sys.stderr)
        if len(vlist) < 50:
            break
        pn += 1
        await asyncio.sleep(0.3)

    out = Path(out_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'up_name': up_name,
        'mid': uid,
        'follower': follower,
        'total': len(all_videos),
        'videos': all_videos,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    # 打印全量表头
    print(f'\n共计 {len(all_videos)} 条视频\n', file=sys.stderr)
    print(f'{"#":>3}  {"BV号":<14} {"时长":>6} {"播放":>10} {"弹幕":>6} {"评论":>5} {"收藏":>6}  标题', file=sys.stderr)
    print('-' * 100, file=sys.stderr)
    for i, v in enumerate(all_videos, 1):
        print(f'{i:>3}  {v["bvid"]:<14} {v["length"]:>6} {v["play"]:>10,} {v["video_review"]:>6,} {v["comment"]:>5,} {v["favorites"]:>6,}   {v["title"][:60]}', file=sys.stderr)

    return payload


if __name__ == '__main__':
    uid = int(sys.argv[1]) if len(sys.argv) > 1 else 520819684
    out_dir = sys.argv[2] if len(sys.argv) > 2 else 'data/小Lin说/videos.json'
    asyncio.run(pull_channel(uid, out_dir))
