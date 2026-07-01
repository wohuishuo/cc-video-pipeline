import argparse
import datetime as dt
import subprocess
from pathlib import Path


def extract_spoken(path: Path) -> list[str]:
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        text = raw.strip()
        if not text:
            continue
        if text.startswith(("#", "|", "---", "```", "【")):
            continue
        if text[:1].isdigit() and ("：" in text[:6] or ":" in text[:6]):
            continue
        lines.append(text)
    return lines


def chunk_lines(lines: list[str], max_chars: int) -> list[str]:
    chunks = []
    buf = []
    size = 0
    for line in lines:
        if buf and size + len(line) + 1 > max_chars:
            chunks.append("\n".join(buf))
            buf = []
            size = 0
        buf.append(line)
        size += len(line) + 1
    if buf:
        chunks.append("\n".join(buf))
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--max-chars", type=int, default=1800)
    parser.add_argument("--voice", default="zh-CN-XiaoxiaoNeural")
    parser.add_argument("--f0-method", default="dio")
    parser.add_argument("--transpose", type=int, default=0)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    script = Path(args.script).resolve()
    out = Path(args.out).resolve()
    work = root / "nahida" / "sovits" / "batch" / dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    chunks_dir = work / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    out.parent.mkdir(parents=True, exist_ok=True)

    chunks = chunk_lines(extract_spoken(script), args.max_chars)
    (work / "chunks.txt").write_text("\n\n---CHUNK---\n\n".join(chunks), encoding="utf-8")
    print(f"[batch] extracted {len(chunks)} chunks -> {work / 'chunks.txt'}", flush=True)

    wavs = []
    ps1 = root / "tools" / "tts-mvp" / "nahida_sovits.ps1"
    for index, text in enumerate(chunks, start=1):
        name = f"nahida_{index:03d}.wav"
        wav = chunks_dir / name
        print(f"[batch] {index:03d}/{len(chunks):03d}: {len(text)} chars", flush=True)
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ps1),
                "-Text",
                text,
                "-Out",
                str(wav),
                "-Voice",
                args.voice,
                "-F0Method",
                args.f0_method,
                "-Transpose",
                str(args.transpose),
            ],
            cwd=root,
            check=True,
        )
        wavs.append(wav)

    concat = work / "concat.txt"
    concat.write_text("\n".join(f"file '{str(w).replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'" for w in wavs), encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(out)], check=True)
    print(f"[ok] Nahida batch output: {out}", flush=True)
    print(f"[ok] Work dir: {work}", flush=True)


if __name__ == "__main__":
    main()
