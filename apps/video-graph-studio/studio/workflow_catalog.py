"""Read-only creator-facing projection of admitted Studio Graph definitions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .contracts import GraphDefinition


WORKFLOW_METADATA: dict[str, dict[str, str]] = {
    "prepared-localization": {"goalId":"prepared-localization","group":"Create","title":"Localize a prepared folder","summary":"Use the compatibility prepared-folder Russian localization workflow.","sourceKind":"prepared","effect":"local-only"},
    "folder-intake": {"goalId":"intake","group":"Prepare","title":"Prepare source media","summary":"Create a verified Source Manifest without transcription.","sourceKind":"folder","effect":"local-only"},
    "url-intake": {"goalId":"intake","group":"Prepare","title":"Prepare source media","summary":"Download one supported social video and create a verified Source Manifest.","sourceKind":"url","effect":"downloads-source"},
    "folder-transcription": {"goalId":"transcribe","group":"Create","title":"Transcribe media","summary":"Create editable transcript JSON and SRT for every source video.","sourceKind":"folder","effect":"local-only"},
    "url-transcription": {"goalId":"transcribe","group":"Create","title":"Transcribe media","summary":"Download and transcribe one supported social video.","sourceKind":"url","effect":"downloads-source"},
    "folder-translation": {"goalId":"translate","group":"Create","title":"Translate subtitles","summary":"Transcribe and translate local videos into selected languages.","sourceKind":"folder","effect":"local-only"},
    "url-translation": {"goalId":"translate","group":"Create","title":"Translate subtitles","summary":"Download, transcribe and translate one social video.","sourceKind":"url","effect":"downloads-source"},
    "folder-voice": {"goalId":"voice","group":"Create","title":"Render translated voices","summary":"Produce resumable translated voice clips without composing final videos.","sourceKind":"folder","effect":"local-only"},
    "url-voice": {"goalId":"voice","group":"Create","title":"Render translated voices","summary":"Download, translate and render voice clips for one social video.","sourceKind":"url","effect":"downloads-source"},
    "folder-dub": {"goalId":"dub","group":"Create","title":"Dub complete videos","summary":"Create translated voice, subtitles and final localized MP4 files.","sourceKind":"folder","effect":"local-only"},
    "url-dub": {"goalId":"dub","group":"Create","title":"Dub complete videos","summary":"Download and create translated, subtitle-burned MP4 files.","sourceKind":"url","effect":"downloads-source"},
    "folder-release": {"goalId":"release","group":"Publish","title":"Prepare a release batch","summary":"Localize media and create private or draft publication plans only.","sourceKind":"folder","effect":"planning-only"},
    "url-release": {"goalId":"release","group":"Publish","title":"Prepare a release batch","summary":"Download, localize and create private or draft publication plans.","sourceKind":"url","effect":"planning-only"},
    "publication-batch-execute": {"goalId":"release-execute","group":"Publish","title":"Execute a release batch","summary":"Upload every confirmed private YouTube plan strictly one at a time.","sourceKind":"run","effect":"contacts-youtube-private"},
    "creator-profile": {"goalId":"creator-profile","group":"Batch","title":"Discover a creator","summary":"Create an ordered manifest of canonical creator video URLs.","sourceKind":"creator","effect":"reads-profile"},
    "creator-batch-dub": {"goalId":"creator-dub","group":"Batch","title":"Dub a creator batch","summary":"Discover and localize every selected creator video strictly serially.","sourceKind":"creator","effect":"downloads-source"},
    "publication-plan": {"goalId":"publication-plan","group":"Publish","title":"Plan one publication","summary":"Fingerprint one finished video and metadata without uploading.","sourceKind":"file","effect":"planning-only"},
    "publication-execute": {"goalId":"publication-execute","group":"Publish","title":"Publish one private video","summary":"Execute one exact confirmed private YouTube publication plan.","sourceKind":"run","effect":"contacts-youtube-private"},
    "youtube-connect": {"goalId":"youtube-connect","group":"Account","title":"Connect YouTube","summary":"Complete desktop OAuth and store the refresh credential in Vault.","sourceKind":"config","effect":"opens-google-consent"},
}


NODE_METADATA: dict[str, dict[str, str]] = {
    "prepared-folder": {"title":"Prepared folder","description":"Resolve and validate the prepared localization batch.","owner":"source-intake","relationship":"Query","loop":"Source","retry":"Read-only query","output":"Prepared source fact"},
    "edge-localize": {"title":"Localize prepared media","description":"Render Russian voice, mix source ambience and burn subtitles.","owner":"localization","relationship":"Adapter","loop":"Localization","retry":"Checkpointed items","output":"Localized MP4"},
    "verify-output": {"title":"Verify localized output","description":"Require inspectable files and matching execution receipts.","owner":"output-verification","relationship":"Policy","loop":"Localization","retry":"Recheck only","output":"Verified output fact"},
    "source-intake": {"title":"Prepare source","description":"Resolve local media or download one supported social source.","owner":"source-intake","relationship":"Command","loop":"Source","retry":"Stable operation checkpoint","output":"Source Manifest"},
    "verify-source": {"title":"Verify source","description":"Check declared media paths, sizes and fingerprints.","owner":"source-intake","relationship":"Policy","loop":"Source","retry":"Recheck only","output":"Verified source fact"},
    "transcribe-source": {"title":"Transcribe media","description":"Run ASR for one verified media item at a time.","owner":"transcription","relationship":"Command","loop":"Transcription","retry":"Per-media checkpoint","output":"Transcript Manifest"},
    "verify-transcript": {"title":"Verify transcripts","description":"Check transcript JSON, SRT and source lineage fingerprints.","owner":"transcription","relationship":"Policy","loop":"Transcription","retry":"Recheck only","output":"Verified transcript fact"},
    "translate-transcript": {"title":"Translate subtitles","description":"Translate one language and media item at a time.","owner":"translation","relationship":"Command","loop":"Translation","retry":"Per-language checkpoint","output":"Translation Manifest"},
    "verify-translation": {"title":"Verify translations","description":"Require exact language coverage and artifact fingerprints.","owner":"translation","relationship":"Policy","loop":"Translation","retry":"Recheck only","output":"Verified translation fact"},
    "render-voice": {"title":"Render translated voice","description":"Synthesize one translated segment at a time with resumable clips.","owner":"voice-rendering","relationship":"Command","loop":"Voice","retry":"Per-segment checkpoint","output":"Voice Manifest"},
    "verify-voice": {"title":"Verify voice clips","description":"Check every audio clip fingerprint, size and measured duration.","owner":"voice-rendering","relationship":"Policy","loop":"Voice","retry":"Recheck only","output":"Verified voice fact"},
    "localize-video": {"title":"Compose localized video","description":"Mix voice and source audio, render subtitles and encode MP4.","owner":"localization","relationship":"Command","loop":"Localization","retry":"Per-derivative checkpoint","output":"Localization Manifest"},
    "verify-localization": {"title":"Verify localized videos","description":"Require exact media and language derivative coverage.","owner":"localization","relationship":"Policy","loop":"Localization","retry":"Recheck only","output":"Verified localization fact"},
    "plan-publication-batch": {"title":"Plan release batch","description":"Create one private or draft Publication Plan per derivative.","owner":"publication-batch","relationship":"Command","loop":"Release planning","retry":"Per-derivative checkpoint","output":"Publication Batch Plan"},
    "verify-publication-batch": {"title":"Verify release plans","description":"Check derivative, metadata, target and child-plan coverage.","owner":"publication-batch","relationship":"Policy","loop":"Release planning","retry":"Recheck only","output":"Verified batch-plan fact"},
    "discover-creator": {"title":"Discover creator videos","description":"Page serially, canonicalize URLs and checkpoint the cursor.","owner":"creator-discovery","relationship":"Command","loop":"Discovery","retry":"Per-page checkpoint","output":"Creator Manifest"},
    "verify-creator": {"title":"Verify creator manifest","description":"Require ordered unique canonical video URLs.","owner":"creator-discovery","relationship":"Policy","loop":"Discovery","retry":"Recheck only","output":"Verified creator fact"},
    "localize-creator-batch": {"title":"Localize creator batch","description":"Run Source, ASR, Translation, Voice and Localization per video.","owner":"creator-batch","relationship":"Command","loop":"Creator batch","retry":"Per-video checkpoint","output":"Creator Batch Manifest"},
    "verify-creator-batch": {"title":"Verify creator batch","description":"Require exact item, language and derivative coverage.","owner":"creator-batch","relationship":"Policy","loop":"Creator batch","retry":"Recheck only","output":"Verified creator-batch fact"},
    "plan-publication": {"title":"Build publication plan","description":"Fingerprint one finished video, metadata and selected targets.","owner":"publication","relationship":"Command","loop":"Publication planning","retry":"Stable operation checkpoint","output":"Publication Plan"},
    "verify-publication-plan": {"title":"Verify publication plan","description":"Check immutable input and target coverage before execution.","owner":"publication","relationship":"Policy","loop":"Publication planning","retry":"Recheck only","output":"Verified publication-plan fact"},
    "execute-publication": {"title":"Execute private publication","description":"Require the exact plan SHA and inject one Vault credential.","owner":"publication","relationship":"Command","loop":"Publication","retry":"Outcome-aware checkpoint","output":"Publication Manifest"},
    "verify-publication-execution": {"title":"Verify publication receipt","description":"Require a fingerprinted receipt and external platform identity.","owner":"publication","relationship":"Policy","loop":"Publication","retry":"Recheck only","output":"Verified publication fact"},
    "execute-publication-batch": {"title":"Execute release batch","description":"Run one confirmed private YouTube child plan at a time.","owner":"publication-batch-execution","relationship":"Command","loop":"Release execution","retry":"Per-child checkpoint; unknown fenced","output":"Batch Execution Manifest"},
    "verify-publication-batch-execution": {"title":"Verify release receipts","description":"Check every child result, external ID and aggregate fingerprint.","owner":"video-graph-studio","relationship":"Policy","loop":"Release execution","retry":"Recheck only","output":"Verified batch-execution fact"},
    "connect-youtube": {"title":"Connect YouTube account","description":"Open consent, validate state and PKCE, and store through Vault.","owner":"youtube-oauth-bootstrap","relationship":"Command","loop":"Account connection","retry":"Restart consent safely","output":"OAuth Bootstrap Receipt"},
    "verify-youtube-credential": {"title":"Verify YouTube credential","description":"Confirm one active provider-bound credential without reading it.","owner":"credential-vault","relationship":"Query","loop":"Account connection","retry":"Read-only query","output":"Active credential fact"},
}


def build_workflow_catalog(
    graphs: Mapping[str, GraphDefinition],
) -> list[dict[str, Any]]:
    """Project exact graph topology plus bounded creator-facing metadata."""

    missing_workflows = set(graphs) - set(WORKFLOW_METADATA)
    extra_workflows = set(WORKFLOW_METADATA) - set(graphs)
    if missing_workflows or extra_workflows:
        raise ValueError(
            f"workflow metadata mismatch: missing={sorted(missing_workflows)}, extra={sorted(extra_workflows)}"
        )

    rows: list[dict[str, Any]] = []
    for template_id, graph in graphs.items():
        value = graph.to_dict()
        projected_nodes = []
        for index, node in enumerate(value["nodes"], start=1):
            metadata = NODE_METADATA.get(node["type"])
            if metadata is None:
                raise ValueError(f"node metadata missing: {node['type']}")
            projected_nodes.append(
                {
                    "id": node["id"],
                    "type": node["type"],
                    "step": index,
                    **metadata,
                }
            )
        rows.append(
            {
                "templateId": template_id,
                **WORKFLOW_METADATA[template_id],
                "revision": value["revision"],
                "nodes": projected_nodes,
                "edges": [
                    {
                        "source": edge["source"],
                        "target": edge["target"],
                        "relationship": edge["relationship"],
                    }
                    for edge in value["edges"]
                ],
            }
        )
    return rows
