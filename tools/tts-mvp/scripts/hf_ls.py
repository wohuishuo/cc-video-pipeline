"""hf_ls.py — 列 HF 仓库文件"""
import requests, sys
url = f"https://huggingface.co/api/datasets/{sys.argv[1]}/tree/main" if len(sys.argv) > 1 and "/" in sys.argv[1] and not sys.argv[1].startswith("http") else None
if url is None:
    url = sys.argv[1]
r = requests.get(url, timeout=30)
print("status:", r.status_code)
r.raise_for_status()
for it in r.json()[:50]:
    print(f"  [{it.get('type','?'):5s}] {it.get('size',0)//1024:>7} KB  {it.get('path','')}")
