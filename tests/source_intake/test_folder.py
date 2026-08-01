from pathlib import Path
import sys

import pytest


APP = Path(__file__).resolve().parents[2] / "apps" / "source-intake"
sys.path.insert(0, str(APP))

from intake.contracts import IntakeError, SourceSpec, classify_url  # noqa: E402
from intake.folder import discover_folder  # noqa: E402


def test_folder_discovery_is_recursive_supported_and_deterministic(tmp_path):
    (tmp_path / "z").mkdir()
    (tmp_path / "z" / "second.MOV").write_bytes(b"22")
    (tmp_path / "first.mp4").write_bytes(b"1")
    (tmp_path / "ignore.txt").write_text("no", encoding="utf-8")

    manifest = discover_folder(SourceSpec.folder(tmp_path))

    assert manifest.source_kind == "folder"
    assert [Path(item.path).name for item in manifest.media] == ["first.mp4", "second.MOV"]
    assert [item.size for item in manifest.media] == [1, 2]
    assert len({item.id for item in manifest.media}) == 2


def test_empty_folder_is_rejected_without_manifest(tmp_path):
    with pytest.raises(IntakeError) as raised:
        discover_folder(SourceSpec.folder(tmp_path))
    assert raised.value.code == "EMPTY_SOURCE"


@pytest.mark.parametrize(
    ("url", "platform"),
    [
        ("https://youtu.be/abc", "youtube"),
        ("https://www.youtube.com/watch?v=abc", "youtube"),
        ("https://b23.tv/abc", "bilibili"),
        ("https://v.douyin.com/abc", "douyin"),
        ("https://www.tiktok.com/@a/video/1", "tiktok"),
    ],
)
def test_url_classification_accepts_only_supported_https_hosts(url, platform):
    assert classify_url(url) == platform
    spec = SourceSpec.url(url)
    assert spec.platform == platform


@pytest.mark.parametrize("url", ["http://youtu.be/x", "https://example.com/x", "not-a-url"])
def test_url_classification_rejects_unsafe_or_unsupported_values(url):
    with pytest.raises(IntakeError) as raised:
        SourceSpec.url(url)
    assert raised.value.code == "UNSUPPORTED_SOURCE"

