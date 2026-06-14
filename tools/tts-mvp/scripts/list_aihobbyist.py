from modelscope.hub.api import HubApi
import json
import sys

api = HubApi()
target = sys.argv[1] if len(sys.argv) > 1 else "aihobbyist/Anime_GPT-Sovits_Models"
files = api.get_model_files(target, recursive=True)
print(f"Files in {target}: {len(files)}")
for f in files[:80]:
    path = f.get("Path", f.get("path", "?"))
    size = f.get("Size", f.get("size", 0))
    ftype = f.get("Type", f.get("type", ""))
    if ftype in ("tree", "directory", "folder"):
        print(f"  [D] {path}/")
    else:
        size_mb = size / 1024 / 1024 if size else 0
        print(f"  [F] {size_mb:8.1f} MB  {path}")
if len(files) > 80:
    print(f"  ... ({len(files) - 80} more)")

