"""aliyun_dump.py — 抓阿里云盘分享内容
非官方 API; 仅用于下载自己分享的资源。

用法: python aliyun_dump.py [out_dir]   (默认 voices/nahida_zh_game/)
"""
import requests
import json
import sys
from pathlib import Path

SHARE_ID = "H92QJFwjcHN"
PWD = "cx88"

s = requests.Session()
s.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.aliyundrive.com/",
})

# 1. 拿 share token
r = s.post(
    "https://api.aliyundrive.com/v2/share_link/get_share_token",
    json={"share_id": SHARE_ID, "share_pwd": PWD},
)
r.raise_for_status()
share_token = r.json()["share_token"]
print("[ok] share_token")

# 2. 拿文件树 (v3 端点)
for endpoint in [
    "https://api.aliyundrive.com/v3/file/list_by_share",
    "https://api.aliyundrive.com/adrive/v3/file/list_by_share",
    "https://api.aliyundrive.com/adrive/v2/file/list_by_share",
]:
    r = s.post(
        endpoint,
        json={"share_id": SHARE_ID, "share_token": share_token, "parent_file_id": "root", "limit": 200},
        headers={"x-share-token": share_token},
    )
    print(f"[try] {endpoint} → {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        break
else:
    print("所有端点都失败，raw:")
    print(r.text[:500])
    sys.exit(1)
# 3. 递归列文件
def list_dir(fid, prefix=""):
    r = s.post(
        "https://api.aliyundrive.com/adrive/v2/file/list_by_share",
        json={"share_id": SHARE_ID, "share_token": share_token, "parent_file_id": fid, "limit": 200},
        headers={"x-share-token": share_token},
    )
    r.raise_for_status()
    data = r.json()
    items = data.get("items", [])
    for it in items:
        name = it.get("name", "?")
        ftype = it.get("type", "?")
        if ftype == "folder":
            list_dir(it["file_id"], prefix + name + "/")
        else:
            size = it.get("size", 0)
            ext = Path(name).suffix.lower()
            if ext in (".wav", ".mp3", ".flac", ".ogg", ".m4a"):
                print(f"  [AUDIO] {size//1024:>7}KB  {prefix}{name}  ({it['file_id']})")
            else:
                print(f"  [skip ] {size//1024:>7}KB  {prefix}{name}")

root_items = data.get("items", [])
for it in root_items:
    if it.get("type") == "folder":
        print(f"\n=== 进入 {it['name']} ===")
        list_dir(it["file_id"], it["name"] + "/")
