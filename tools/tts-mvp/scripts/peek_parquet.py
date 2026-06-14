"""streaming 下载纳西妲日语 wav - 直接读 raw bytes"""
import os
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "300"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
from datasets import load_dataset
import pyarrow.parquet as pq
import io
from pathlib import Path
import time

OUT = Path(r"C:\Users\艾莉\Videos\cc视频剪辑\tools\tts-mvp\voices\nahida_jp\raw")
OUT.mkdir(parents=True, exist_ok=True)

# 逐个 parquet 下载, 每下载一个就用 pyarrow 直接读, 不通过 datasets 音频解码
BASE = "https://huggingface.co/datasets/OpenSpeechHub/Genshin-Voice-Ja/resolve/main/data"
N_PARQUETS = 152
saved = 0
scanned = 0
start = time.time()

from huggingface_hub import hf_hub_download

for i in range(N_PARQUETS):
    fn = f"train-{i:05d}-of-00152.parquet"
    print(f"\n[{i+1}/{N_PARQUETS}] {fn}")
    try:
        p = hf_hub_download(
            repo_id="OpenSpeechHub/Genshin-Voice-Ja",
            filename=f"data/{fn}",
            repo_type="dataset",
            local_dir=r"C:\Users\艾莉\Videos\cc视频剪辑\tools\tts-mvp\voices\nahida_jp\_parquet_cache",
        )
    except Exception as e:
        print(f"  download fail: {e}")
        continue
    # 读 parquet (用 pyarrow.dataset 支持 row filter)
    import pyarrow.dataset as pds
    ds = pds.dataset(p, format="parquet")
    table = ds.to_table(
        columns=["id", "audio", "text", "speaker"],
        filter=(pds.field("speaker") == "Nahida"),
    )
    df = table.to_pandas()
    scanned += pds.dataset(p, format="parquet").count_rows()
    for _, row in df.iterrows():
        audio = row["audio"]
        if isinstance(audio, dict) and audio.get("bytes"):
            wav_bytes = audio["bytes"]
            text = (row.get("text", "") or "")[:60].replace("/", "_").replace("\\", "_")
            sid = row.get("id", "x")
            out_path = OUT / f"{sid}_{text}.wav"
            if not out_path.exists():
                out_path.write_bytes(wav_bytes)
                saved += 1
    elapsed = time.time() - start
    rate = scanned / elapsed if elapsed > 0 else 0
    print(f"  Nahida so far: {saved}  (scanned {scanned} rows, {rate:.0f} rows/s)")
    # 删 parquet 缓存（用完就丢）
    try:
        Path(p).unlink()
    except Exception:
        pass

print(f"\nDONE: scanned {scanned} rows, saved {saved} Nahida wav → {OUT}")



