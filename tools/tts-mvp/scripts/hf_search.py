"""hf_search.py — HuggingFace 搜模型/数据集"""
import requests
import sys

q = sys.argv[1] if len(sys.argv) > 1 else "qwen3 tts"
print(f"q={q}")

# Models
r = requests.get(
    "https://huggingface.co/api/models",
    params={"search": q, "limit": 30},
    timeout=30,
)
r.raise_for_status()
models = r.json()
print(f"\n=== Models ({len(models)}) ===")
for m in models:
    print(f"  {m.get('id')} | downloads: {m.get('downloads', 0)} | likes: {m.get('likes', 0)}")

# Datasets
r = requests.get(
    "https://huggingface.co/api/datasets",
    params={"search": q, "limit": 30},
    timeout=30,
)
r.raise_for_status()
ds = r.json()
print(f"\n=== Datasets ({len(ds)}) ===")
for d in ds:
    print(f"  {d.get('id')} | downloads: {d.get('downloads', 0)}")
