import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(cmd, **kw):
    return subprocess.run(
        cmd, cwd=ROOT, capture_output=True, text=True,
        shell=True, encoding="utf-8", errors="replace", **kw
    )


def main():
    if not (ROOT / ".git").exists():
        run("git init")
        run("git config user.email test@example.com")
        run("git config user.name test")

    # Reset staging
    run("git reset 2>$null")

    # Stage all
    run("git add -A")

    # Get staged files using porcelain format (UTF-8)
    res = run("git status --porcelain")
    staged = []
    ignored = []
    for line in res.stdout.splitlines():
        if not line.strip():
            continue
        # Format: "XY  path"  (2 chars status + space + path)
        # !! = ignored
        if line.startswith("!!"):
            ignored.append(line[3:].strip().replace("\\", "/"))
        elif line.startswith("??"):
            continue  # untracked, not staged
        else:
            path = line[3:].strip().replace("\\", "/")
            # Skip rename pairs
            if " -> " in path:
                path = path.split(" -> ")[-1]
            staged.append(path)

    # Sensitivity check
    SENSITIVE = [
        "cookies.txt", "SESSDATA",
        "video.mp4", "video.m4s", "video.f", "video.mkv", "video.webm",
        "video.jpg", "video.png", "video.webp",
        "audio.wav", "audio.m4a", "audio.mp3", "audio_hq.wav",
        ".info.json", "montage_", "frames/grid_", "frames/cut_",
    ]
    sensitive = [s for s in staged if any(p in s for p in SENSITIVE)]

    # Filter out venv noise
    meaningful = [s for s in staged
                  if "site-packages" not in s and ".venv" not in s]

    print("=== SUMMARY ===")
    print(f"  Staged (raw):       {len(staged)}")
    print(f"  Meaningful:         {len(meaningful)}")
    print(f"  Ignored:            {len(ignored)}")
    print(f"  Sensitive in stage: {len(sensitive)}")

    if sensitive:
        print("\n!!! PROBLEM !!!")
        for s in sensitive:
            print(f"  {s}")
        sys.exit(1)
    else:
        print("OK - no sensitive files")

    print("\n=== MEANINGFUL COMMITS (sorted) ===")
    for s in sorted(meaningful):
        print(f"  {s}")


if __name__ == "__main__":
    main()

