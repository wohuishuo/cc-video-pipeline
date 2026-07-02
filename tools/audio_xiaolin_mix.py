import argparse
import re
import subprocess
import wave
from pathlib import Path


SCENE_RE = re.compile(r"\{\s*id:\s*(\d+),\s*start:\s*(\d+),\s*end:\s*(\d+),\s*chapter:\s*\"([^\"]+)\",\s*kind:\s*\"([^\"]+)\"")


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / wf.getframerate()


def parse_scenes(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    scenes = []
    for match in SCENE_RE.finditer(text):
        scenes.append(
            {
                "id": int(match.group(1)),
                "start": float(match.group(2)),
                "end": float(match.group(3)),
                "chapter": match.group(4),
                "kind": match.group(5),
            }
        )
    if not scenes:
        raise RuntimeError(f"No scenes parsed from {path}")
    return scenes


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def make_silence(path: Path, seconds: float, sr: int = 44100) -> None:
    run([
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"anullsrc=r={sr}:cl=mono",
        "-t", f"{seconds:.3f}",
        "-c:a", "pcm_s16le",
        str(path),
    ])


def render_music(path: Path, seconds: float) -> None:
    # Original restrained bed: low drone, soft upper tone, filtered texture.
    run([
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"sine=frequency=55:sample_rate=44100:duration={seconds:.3f}",
        "-f", "lavfi",
        "-i", f"sine=frequency=110:sample_rate=44100:duration={seconds:.3f}",
        "-f", "lavfi",
        "-i", f"sine=frequency=220:sample_rate=44100:duration={seconds:.3f}",
        "-f", "lavfi",
        "-i", f"anoisesrc=color=pink:sample_rate=44100:duration={seconds:.3f}:amplitude=0.03",
        "-filter_complex",
        "[0:a]volume=0.10[bass];"
        "[1:a]volume=0.035[mid];"
        "[2:a]volume=0.012,atempo=1.0[air];"
        "[3:a]lowpass=f=1800,highpass=f=160,volume=0.05[noise];"
        "[bass][mid][air][noise]amix=inputs=4:duration=first,"
        "afade=t=in:st=0:d=2,"
        "afade=t=out:st={:.3f}:d=3,"
        "alimiter=limit=0.45[out]".format(max(0, seconds - 3)),
        "-map", "[out]",
        "-c:a", "pcm_s16le",
        str(path),
    ])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", required=True)
    parser.add_argument("--scenes", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--work", default="")
    args = parser.parse_args()

    voice = Path(args.voice).resolve()
    scenes_path = Path(args.scenes).resolve()
    out = Path(args.out).resolve()
    work = Path(args.work).resolve() if args.work else out.parent / "mix_work"
    work.mkdir(parents=True, exist_ok=True)
    out.parent.mkdir(parents=True, exist_ok=True)

    dur = wav_duration(voice)
    scenes = parse_scenes(scenes_path)
    scale = dur / 1800.0

    concat_lines = []
    last = 0.0
    segment_index = 0
    silence_cache: dict[float, Path] = {}

    def silence_file(seconds: float) -> Path:
        key = round(seconds, 2)
        if key not in silence_cache:
            p = work / f"silence_{key:.2f}.wav"
            make_silence(p, key)
            silence_cache[key] = p
        return silence_cache[key]

    boundaries = []
    for scene in scenes[1:]:
        boundary = scene["start"] * scale
        prev = scenes[scene["id"] - 2]
        pause = 0.18
        if scene["chapter"] != prev["chapter"]:
            pause = 0.85
        if prev["kind"] in {"title", "question"} or scene["kind"] in {"title", "question"}:
            pause = max(pause, 0.55)
        if scene["id"] in {4, 5, 10, 14, 18, 27, 30, 32, 38}:
            pause = max(pause, 0.9)
        boundaries.append((boundary, pause))

    for boundary, pause in boundaries:
        if boundary <= last + 0.05 or boundary >= dur:
            continue
        segment = work / f"voice_seg_{segment_index:03d}.wav"
        run([
            "ffmpeg", "-y",
            "-i", str(voice),
            "-ss", f"{last:.3f}",
            "-to", f"{boundary:.3f}",
            "-c:a", "pcm_s16le",
            str(segment),
        ])
        concat_lines.append(f"file '{segment.as_posix()}'")
        concat_lines.append(f"file '{silence_file(pause).as_posix()}'")
        segment_index += 1
        last = boundary

    tail = work / f"voice_seg_{segment_index:03d}.wav"
    run([
        "ffmpeg", "-y",
        "-i", str(voice),
        "-ss", f"{last:.3f}",
        "-c:a", "pcm_s16le",
        str(tail),
    ])
    concat_lines.append(f"file '{tail.as_posix()}'")

    concat = work / "voice_with_pauses.concat.txt"
    concat.write_text("\n".join(concat_lines), encoding="utf-8")
    paused_voice = work / "voice_with_pauses.wav"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c:a", "pcm_s16le", str(paused_voice)])

    final_dur = wav_duration(paused_voice)
    music = work / "music_bed.wav"
    render_music(music, final_dur)

    run([
        "ffmpeg", "-y",
        "-i", str(paused_voice),
        "-i", str(music),
        "-filter_complex",
        "[0:a]acompressor=threshold=-18dB:ratio=2.2:attack=8:release=120,volume=1.05[v];"
        "[1:a]volume=0.56[m];"
        "[v][m]amix=inputs=2:duration=first:weights=1 0.55,alimiter=limit=0.95[out]",
        "-map", "[out]",
        "-c:a", "pcm_s16le",
        str(out),
    ])

    preview = out.with_name(out.stem + "-preview-90s.mp3")
    run(["ffmpeg", "-y", "-i", str(out), "-t", "90", "-c:a", "libmp3lame", "-b:a", "192k", str(preview)])
    print(f"[ok] voice input duration: {dur:.2f}s")
    print(f"[ok] mixed duration: {final_dur:.2f}s")
    print(f"[ok] output: {out}")
    print(f"[ok] preview: {preview}")


if __name__ == "__main__":
    main()
