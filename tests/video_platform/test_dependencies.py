import re
from pathlib import Path

from video_platform.dependencies import DependencyManifest


def test_uploader_dependency_is_pinned_to_full_git_revision():
    manifest = DependencyManifest.load(Path("vendor/video-uploaders.lock.json"))
    dependency = manifest.dependencies["social-auto-upload"]
    assert dependency.url == "https://github.com/dreammis/social-auto-upload.git"
    assert re.fullmatch(r"[0-9a-f]{40}", dependency.revision)
    assert dependency.license == "GPL-3.0"


def test_dependency_checkout_path_is_project_relative():
    manifest = DependencyManifest.load(Path("vendor/video-uploaders.lock.json"))
    assert not manifest.dependencies["social-auto-upload"].checkout.is_absolute()
