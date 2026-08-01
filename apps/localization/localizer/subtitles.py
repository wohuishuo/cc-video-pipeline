"""Russian ASS subtitle generation for the fixed lower caption band."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import textwrap
from typing import Any, Sequence


@dataclass(frozen=True)
class AssEvent:
    start: float
    end: float
    text: str


def _escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")


def _wrapped(text: str, width: int = 48) -> str:
    lines = textwrap.wrap(" ".join(text.split()), width=width, break_long_words=False)
    if not lines:
        return ""
    if len(lines) > 2:
        lines = [lines[0], " ".join(lines[1:])]
    return r"\N".join(lines[:2])


def ass_event(segment: dict[str, Any], *, play_res: tuple[int, int]) -> AssEvent:
    del play_res
    text = segment.get("text_ru", segment.get("text", ""))
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Russian subtitle text is required")
    start = float(segment["start"])
    end = float(segment["end"])
    if start < 0 or end <= start:
        raise ValueError("invalid subtitle timing")
    return AssEvent(start, end, _wrapped(_escape(text)))


def _time(seconds: float) -> str:
    centiseconds = round(seconds * 100)
    hours, centiseconds = divmod(centiseconds, 360_000)
    minutes, centiseconds = divmod(centiseconds, 6_000)
    whole, centiseconds = divmod(centiseconds, 100)
    return f"{hours}:{minutes:02}:{whole:02}.{centiseconds:02}"


def write_ass(
    segments: Sequence[dict[str, Any]], path: str | Path, *, play_res: tuple[int, int]
) -> Path:
    width, height = play_res
    font_size = max(24, round(height * 0.044))
    margin_v = max(18, round(height * 0.035))
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Russian,Arial,{font_size},&H00FFFFFF,&H000000FF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,48,48,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for raw in segments:
        event = ass_event(raw, play_res=play_res)
        events.append(
            f"Dialogue: 0,{_time(event.start)},{_time(event.end)},Russian,,0,0,0,,{event.text}"
        )
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(header + "\n".join(events) + "\n", encoding="utf-8-sig")
    return target
