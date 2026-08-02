from pathlib import Path

from scripts.validate_mvp_manifests import validate_repository


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_APPS = {
    "platform-io", "transcription", "signal-analysis", "frame-extraction",
    "video-editing", "localization", "voice-cloning", "channel-research",
    "remotion-studio", "source-intake", "translation", "video-graph-studio", "voice-rendering",
    "creator-discovery",
    "publication",
    "workspace-access",
    "workspace-storage",
    "credential-vault",
    "client-contracts",
}


def test_every_expected_mvp_has_a_valid_manifest():
    actual = {path.parent.name for path in (ROOT / "apps").glob("*/mvp.json")}
    assert actual == EXPECTED_APPS
    assert validate_repository(ROOT) == []


def test_root_readme_is_english_and_links_every_mvp():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Video Production MVPs" in text
    assert "Ã" not in text and "â€" not in text
    for name in EXPECTED_APPS:
        assert f"apps/{name}/README.md" in text


def test_repository_guides_are_clean_english_and_commands_exist():
    for relative in ("TOOLS.md", "docs/PROJECT_MAP.md"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "Ã" not in text and "â€" not in text
        assert "MVP" in text
    assert (ROOT / "scripts/doctor.ps1").is_file()
    assert (ROOT / "scripts/test-all.ps1").is_file()


def test_every_mvp_has_four_evidence_artifacts():
    required = {"vertical-slice-brief.md", "capability-dag.md", "capability-evidence.md", "delivery-ledger.md"}
    for name in EXPECTED_APPS:
        evidence = ROOT / "docs" / "mvp" / name
        assert {path.name for path in evidence.glob("*.md")} >= required


def test_reusable_applications_contain_no_generated_media():
    forbidden = {".mp3", ".wav", ".mp4", ".mov", ".mkv", ".pid", ".pth", ".bin"}
    offenders = [path for path in (ROOT / "apps").rglob("*") if path.is_file() and path.suffix.lower() in forbidden]
    assert offenders == []


def test_readme_is_a_visual_documentation_hub():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert text.count("```mermaid") >= 2
    assert "Delivery evidence" in text
    assert "DOMAIN_VERIFIED" in text
    for relative in ("docs/ARCHITECTURE.md", "docs/WORKFLOWS.md", "docs/CONTRIBUTING.md"):
        assert f"]({relative})" in text
        assert (ROOT / relative).is_file()


def test_documentation_pages_include_workflow_and_ownership_diagrams():
    architecture = (ROOT / "docs/ARCHITECTURE.md").read_text(encoding="utf-8")
    workflows = (ROOT / "docs/WORKFLOWS.md").read_text(encoding="utf-8")
    contributing = (ROOT / "docs/CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "```mermaid" in architecture
    assert workflows.count("```mermaid") >= 3
    assert "mvp.json" in contributing
    assert "Generated artifacts" in contributing
