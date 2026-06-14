"""hf_readme.py — 读 HF 数据集 README"""
import requests, sys
repo = sys.argv[1]
url = f"https://huggingface.co/datasets/{repo}/raw/main/README.md"
r = requests.get(url, timeout=30, allow_redirects=True)
print(f"status: {r.status_code}, len: {len(r.text)}")
print(r.text[:3000])