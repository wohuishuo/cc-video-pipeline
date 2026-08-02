from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio"
sys.path.insert(0, str(APP))

from studio.api import (  # noqa: E402
    CREATOR_BATCH_GRAPHS,
    CREATOR_CAMPAIGN_GRAPHS,
    CREATOR_GRAPHS,
    INTAKE_GRAPHS,
    LOCALIZATION_GRAPHS,
    PREPARED_FOLDER_GRAPH,
    PUBLICATION_BATCH_EXECUTION_GRAPHS,
    PUBLICATION_EXECUTION_GRAPHS,
    PUBLICATION_GRAPHS,
    RELEASE_GRAPHS,
    TRANSCRIPTION_GRAPHS,
    TRANSLATION_GRAPHS,
    VOICE_GRAPHS,
    YOUTUBE_CONNECT_GRAPHS,
    StudioApplication,
)
from studio.engine import WorkflowEngine  # noqa: E402
from studio.store import RunStore  # noqa: E402


def application(tmp_path):
    store = RunStore(tmp_path / "studio.db")
    return StudioApplication(
        store,
        WorkflowEngine(store, {}),
        allowed_roots=(tmp_path,),
    )


def expected_graphs():
    return {
        "prepared-localization": PREPARED_FOLDER_GRAPH,
        **INTAKE_GRAPHS,
        **TRANSCRIPTION_GRAPHS,
        **TRANSLATION_GRAPHS,
        **VOICE_GRAPHS,
        **LOCALIZATION_GRAPHS,
        **RELEASE_GRAPHS,
        **CREATOR_GRAPHS,
        **CREATOR_BATCH_GRAPHS,
        **CREATOR_CAMPAIGN_GRAPHS,
        **PUBLICATION_GRAPHS,
        **PUBLICATION_EXECUTION_GRAPHS,
        **PUBLICATION_BATCH_EXECUTION_GRAPHS,
        **YOUTUBE_CONNECT_GRAPHS,
    }


def test_catalog_projects_every_admissible_graph_without_topology_drift(tmp_path):
    status, response = application(tmp_path).handle(
        "GET", "/api/v1/capabilities", {}, None
    )
    rows = response["capabilities"]
    by_template = {row["templateId"]: row for row in rows}

    assert status == 200
    assert set(by_template) == set(expected_graphs())
    for template_id, graph in expected_graphs().items():
        expected = graph.to_dict()
        projected = by_template[template_id]
        assert projected["revision"] == expected["revision"]
        assert [node["id"] for node in projected["nodes"]] == [
            node["id"] for node in expected["nodes"]
        ]
        assert [
            {
                "source": edge["source"],
                "target": edge["target"],
                "relationship": edge["relationship"],
            }
            for edge in projected["edges"]
        ] == expected["edges"]


def test_catalog_explains_url_translation_as_six_real_steps_and_loops(tmp_path):
    _, response = application(tmp_path).handle(
        "GET", "/api/v1/capabilities", {}, None
    )
    workflow = next(
        row for row in response["capabilities"] if row["templateId"] == "url-translation"
    )

    assert workflow["goalId"] == "translate"
    assert workflow["group"] == "Create"
    assert workflow["sourceKind"] == "url"
    assert workflow["effect"] == "downloads-source"
    assert workflow["requirements"] == [
        "source-url",
        "asr",
        "languages",
        "translation",
    ]
    assert [node["id"] for node in workflow["nodes"]] == [
        "intake",
        "verify-source",
        "transcribe",
        "verify-transcript",
        "translate",
        "verify-translation",
    ]
    assert [node["loop"] for node in workflow["nodes"]] == [
        "Source",
        "Source",
        "Transcription",
        "Transcription",
        "Translation",
        "Translation",
    ]
    assert [edge["relationship"] for edge in workflow["edges"]] == ["Fact"] * 5


def test_catalog_marks_platform_contact_separately_from_planning(tmp_path):
    _, response = application(tmp_path).handle(
        "GET", "/api/v1/capabilities", {}, None
    )
    effects = {row["templateId"]: row["effect"] for row in response["capabilities"]}

    assert effects["publication-plan"] == "planning-only"
    assert effects["folder-release"] == "planning-only"
    assert effects["publication-execute"] == "contacts-youtube-private"
    assert effects["publication-batch-execute"] == "contacts-youtube-private"
