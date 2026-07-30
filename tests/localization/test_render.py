from pathlib import Path
import sys

LOCALIZATION_ROOT = Path(__file__).resolve().parents[2] / "apps" / "localization"
sys.path.insert(0, str(LOCALIZATION_ROOT))

from localizer.render import build_video_filter  # noqa: E402
from localizer.subtitles import ass_event, write_ass  # noqa: E402


def test_ass_keeps_timecodes_and_wraps_to_at_most_two_lines(tmp_path):
    segment = {
        "id": 1,
        "start": 1.25,
        "end": 5.5,
        "text_ru": "Очень длинное русское предложение для технического промышленного видеоролика",
    }
    event = ass_event(segment, play_res=(1280, 720))
    assert event.start == 1.25
    assert event.end == 5.5
    assert event.text.count(r"\N") <= 1
    target = tmp_path / "ru.ass"
    write_ass([segment], target, play_res=(1280, 720))
    assert "Dialogue: 0,0:00:01.25,0:00:05.50" in target.read_text(encoding="utf-8-sig")


def test_caption_band_filter_scales_and_burns_ass():
    graph = build_video_filter(width=1270, height=720, ass_path="C:/tmp/ru.ass")
    assert "crop=1270:140:0:580" in graph
    assert "boxblur" in graph
    assert "ass=" in graph
    assert "drawbox" in graph
