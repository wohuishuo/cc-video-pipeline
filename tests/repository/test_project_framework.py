from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_project_framework_has_every_operating_layer():
    required = {
        "docs/project/product/creator-automation-studio.md",
        "docs/project/capabilities/video-automation-capability-map.md",
        "docs/project/architecture/system-component-map.md",
        "docs/project/architecture/component-catalog.md",
        "docs/project/decisions/ADR-001-graph-process-manager.md",
        "docs/project/engineering/graph-loop-operating-model.md",
        "docs/project/evidence/README.md",
        "docs/project/planning/capability-roadmap.md",
        "docs/project/reviews/graph-loop-dependency-review.md",
        "docs/training/01-independent-video-mvps-to-browser-workflow.md",
    }
    assert all((ROOT / relative).is_file() for relative in required)


def test_graph_loop_documents_encode_ownership_and_evidence_rules():
    architecture = (ROOT / "docs/project/architecture/system-component-map.md").read_text(encoding="utf-8")
    operating_model = (ROOT / "docs/project/engineering/graph-loop-operating-model.md").read_text(encoding="utf-8")
    capability_map = (ROOT / "docs/project/capabilities/video-automation-capability-map.md").read_text(encoding="utf-8")
    assert architecture.count("```mermaid") >= 2
    assert "one authoritative writer" in architecture.lower()
    assert "Loop Engineering" in operating_model
    assert "Graph Engineering" in operating_model
    assert "operationId" in operating_model and "inputFingerprint" in operating_model
    assert "committed fact" in operating_model.lower()
    assert "Source Intake" in capability_map
    assert "Transcription" in capability_map
    assert "Publication" in capability_map


def test_project_index_links_the_framework():
    project = (ROOT / "docs/project/README.md").read_text(encoding="utf-8")
    for relative in (
        "product/creator-automation-studio.md",
        "capabilities/video-automation-capability-map.md",
        "architecture/system-component-map.md",
        "architecture/component-catalog.md",
        "engineering/graph-loop-operating-model.md",
        "planning/capability-roadmap.md",
    ):
        assert f"]({relative})" in project
