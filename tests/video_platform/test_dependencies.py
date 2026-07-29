import re
from pathlib import Path

from video_platform.dependencies import DependencyManifest, ensure_runtime_config


def test_uploader_dependency_is_pinned_to_full_git_revision():
    manifest = DependencyManifest.load(Path("vendor/video-uploaders.lock.json"))
    dependency = manifest.dependencies["social-auto-upload"]
    assert dependency.url == "https://github.com/dreammis/social-auto-upload.git"
    assert re.fullmatch(r"[0-9a-f]{40}", dependency.revision)
    assert dependency.license == "GPL-3.0"


def test_dependency_checkout_path_is_project_relative():
    manifest = DependencyManifest.load(Path("vendor/video-uploaders.lock.json"))
    assert not manifest.dependencies["social-auto-upload"].checkout.is_absolute()


def test_runtime_config_is_created_from_upstream_example(tmp_path):
    (tmp_path / "conf.example.py").write_text("BASE_DIR = 'example'\n", encoding="utf-8")
    created = ensure_runtime_config(tmp_path)
    assert created == tmp_path / "conf.py"
    assert created.read_text(encoding="utf-8") == "BASE_DIR = 'example'\n"
