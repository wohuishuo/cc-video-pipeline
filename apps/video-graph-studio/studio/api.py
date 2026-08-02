"""Versioned application API independent of the HTTP transport."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

from .contracts import ContractError, GraphDefinition
from .creator_catalog import project_creator_catalog
from .engine import WorkflowEngine
from .language_catalog import SUPPORTED_LANGUAGE_LOCALES, language_rows
from .store import CreateRun, RunStore
from .workflow_catalog import build_workflow_catalog


PREPARED_FOLDER_GRAPH = GraphDefinition.from_dict(
    {
        "schemaVersion": 1,
        "graphId": "prepared-folder-edge",
        "revision": 1,
        "nodes": [
            {"id": "source", "type": "prepared-folder", "config": {}},
            {"id": "localize", "type": "edge-localize", "config": {}},
            {"id": "verify", "type": "verify-output", "config": {}},
        ],
        "edges": [
            {"source": "source", "target": "localize", "relationship": "Fact"},
            {"source": "localize", "target": "verify", "relationship": "Fact"},
        ],
    }
)

INTAKE_GRAPHS = {
    template_id: GraphDefinition.from_dict(
        {
            "schemaVersion": 1,
            "graphId": template_id,
            "revision": 1,
            "nodes": [
                {"id": "intake", "type": "source-intake", "config": {"mode": mode}},
                {"id": "verify", "type": "verify-source", "config": {}},
            ],
            "edges": [{"source": "intake", "target": "verify", "relationship": "Fact"}],
        }
    )
    for template_id, mode in (("folder-intake", "folder"), ("url-intake", "url"))
}

TRANSCRIPTION_GRAPHS = {
    template_id: GraphDefinition.from_dict(
        {
            "schemaVersion": 1,
            "graphId": template_id,
            "revision": 1,
            "nodes": [
                {"id": "intake", "type": "source-intake", "config": {"mode": mode}},
                {"id": "verify-source", "type": "verify-source", "config": {}},
                {"id": "transcribe", "type": "transcribe-source", "config": {}},
                {"id": "verify-transcript", "type": "verify-transcript", "config": {}},
            ],
            "edges": [
                {"source": "intake", "target": "verify-source", "relationship": "Fact"},
                {"source": "verify-source", "target": "transcribe", "relationship": "Fact"},
                {"source": "transcribe", "target": "verify-transcript", "relationship": "Fact"},
            ],
        }
    )
    for template_id, mode in (
        ("folder-transcription", "folder"),
        ("url-transcription", "url"),
    )
}

TRANSLATION_GRAPHS = {
    template_id: GraphDefinition.from_dict(
        {
            "schemaVersion": 1,
            "graphId": template_id,
            "revision": 1,
            "nodes": [
                {"id": "intake", "type": "source-intake", "config": {"mode": mode}},
                {"id": "verify-source", "type": "verify-source", "config": {}},
                {"id": "transcribe", "type": "transcribe-source", "config": {}},
                {"id": "verify-transcript", "type": "verify-transcript", "config": {}},
                {"id": "translate", "type": "translate-transcript", "config": {}},
                {"id": "verify-translation", "type": "verify-translation", "config": {}},
            ],
            "edges": [
                {"source": "intake", "target": "verify-source", "relationship": "Fact"},
                {"source": "verify-source", "target": "transcribe", "relationship": "Fact"},
                {"source": "transcribe", "target": "verify-transcript", "relationship": "Fact"},
                {"source": "verify-transcript", "target": "translate", "relationship": "Fact"},
                {"source": "translate", "target": "verify-translation", "relationship": "Fact"},
            ],
        }
    )
    for template_id, mode in (
        ("folder-translation", "folder"),
        ("url-translation", "url"),
    )
}

VOICE_GRAPHS = {
    template_id: GraphDefinition.from_dict(
        {
            "schemaVersion": 1, "graphId": template_id, "revision": 1,
            "nodes": [
                {"id": "intake", "type": "source-intake", "config": {"mode": mode}},
                {"id": "verify-source", "type": "verify-source", "config": {}},
                {"id": "transcribe", "type": "transcribe-source", "config": {}},
                {"id": "verify-transcript", "type": "verify-transcript", "config": {}},
                {"id": "translate", "type": "translate-transcript", "config": {}},
                {"id": "verify-translation", "type": "verify-translation", "config": {}},
                {"id": "render-voice", "type": "render-voice", "config": {}},
                {"id": "verify-voice", "type": "verify-voice", "config": {}},
            ],
            "edges": [
                {"source": left, "target": right, "relationship": "Fact"}
                for left, right in zip(
                    ("intake", "verify-source", "transcribe", "verify-transcript", "translate", "verify-translation", "render-voice"),
                    ("verify-source", "transcribe", "verify-transcript", "translate", "verify-translation", "render-voice", "verify-voice"),
                )
            ],
        }
    )
    for template_id, mode in (("folder-voice", "folder"), ("url-voice", "url"))
}

LOCALIZATION_GRAPHS = {
    template_id: GraphDefinition.from_dict(
        {
            "schemaVersion": 1, "graphId": template_id, "revision": 1,
            "nodes": [
                {"id": "intake", "type": "source-intake", "config": {"mode": mode}},
                {"id": "verify-source", "type": "verify-source", "config": {}},
                {"id": "transcribe", "type": "transcribe-source", "config": {}},
                {"id": "verify-transcript", "type": "verify-transcript", "config": {}},
                {"id": "translate", "type": "translate-transcript", "config": {}},
                {"id": "verify-translation", "type": "verify-translation", "config": {}},
                {"id": "render-voice", "type": "render-voice", "config": {}},
                {"id": "verify-voice", "type": "verify-voice", "config": {}},
                {"id": "localize-video", "type": "localize-video", "config": {}},
                {"id": "verify-localization", "type": "verify-localization", "config": {}},
            ],
            "edges": [
                {"source": left, "target": right, "relationship": "Fact"}
                for left, right in zip(
                    ("intake", "verify-source", "transcribe", "verify-transcript", "translate", "verify-translation", "render-voice", "verify-voice", "localize-video"),
                    ("verify-source", "transcribe", "verify-transcript", "translate", "verify-translation", "render-voice", "verify-voice", "localize-video", "verify-localization"),
                )
            ],
        }
    )
    for template_id, mode in (("folder-dub", "folder"), ("url-dub", "url"))
}

RELEASE_GRAPHS = {}
for template_id, localization_id in (("folder-release", "folder-dub"), ("url-release", "url-dub")):
    base = LOCALIZATION_GRAPHS[localization_id].to_dict()
    base["graphId"] = template_id
    base["nodes"].extend(
        [
            {"id": "plan-publication-batch", "type": "plan-publication-batch", "config": {}},
            {"id": "verify-publication-batch", "type": "verify-publication-batch", "config": {}},
        ]
    )
    base["edges"].extend(
        [
            {"source": "verify-localization", "target": "plan-publication-batch", "relationship": "Fact"},
            {"source": "plan-publication-batch", "target": "verify-publication-batch", "relationship": "Fact"},
        ]
    )
    RELEASE_GRAPHS[template_id] = GraphDefinition.from_dict(base)

CREATOR_GRAPHS = {
    "creator-profile": GraphDefinition.from_dict(
        {
            "schemaVersion": 1,
            "graphId": "creator-profile",
            "revision": 1,
            "nodes": [
                {"id": "discover-creator", "type": "discover-creator", "config": {}},
                {"id": "verify-creator", "type": "verify-creator", "config": {}},
            ],
            "edges": [{"source": "discover-creator", "target": "verify-creator", "relationship": "Fact"}],
        }
    )
}

CREATOR_BATCH_GRAPHS = {
    "creator-batch-dub": GraphDefinition.from_dict(
        {
            "schemaVersion": 1,
            "graphId": "creator-batch-dub",
            "revision": 1,
            "nodes": [
                {"id": "discover-creator", "type": "discover-creator", "config": {}},
                {"id": "verify-creator", "type": "verify-creator", "config": {}},
                {"id": "localize-creator-batch", "type": "localize-creator-batch", "config": {}},
                {"id": "verify-creator-batch", "type": "verify-creator-batch", "config": {}},
            ],
            "edges": [
                {"source": "discover-creator", "target": "verify-creator", "relationship": "Fact"},
                {"source": "verify-creator", "target": "localize-creator-batch", "relationship": "Fact"},
                {"source": "localize-creator-batch", "target": "verify-creator-batch", "relationship": "Fact"},
            ],
        }
    )
}

CREATOR_CAMPAIGN_GRAPHS = {
    "creator-campaign": GraphDefinition.from_dict(
        {
            "schemaVersion": 1,
            "graphId": "creator-campaign",
            "revision": 1,
            "nodes": [
                {"id": "select-creator-videos", "type": "select-creator-videos", "config": {}},
                {"id": "verify-selection", "type": "verify-selection", "config": {}},
                {"id": "localize-creator-batch", "type": "localize-creator-batch", "config": {}},
                {"id": "verify-creator-batch", "type": "verify-creator-batch", "config": {}},
            ],
            "edges": [
                {"source": "select-creator-videos", "target": "verify-selection", "relationship": "Fact"},
                {"source": "verify-selection", "target": "localize-creator-batch", "relationship": "Fact"},
                {"source": "localize-creator-batch", "target": "verify-creator-batch", "relationship": "Fact"},
            ],
        }
    )
}

PUBLICATION_GRAPHS = {
    "publication-plan": GraphDefinition.from_dict(
        {
            "schemaVersion": 1,
            "graphId": "publication-plan",
            "revision": 1,
            "nodes": [
                {"id": "plan-publication", "type": "plan-publication", "config": {}},
                {"id": "verify-publication-plan", "type": "verify-publication-plan", "config": {}},
            ],
            "edges": [{"source": "plan-publication", "target": "verify-publication-plan", "relationship": "Fact"}],
        }
    )
}

PUBLICATION_EXECUTION_GRAPHS = {
    "publication-execute": GraphDefinition.from_dict(
        {
            "schemaVersion": 1,
            "graphId": "publication-execute",
            "revision": 1,
            "nodes": [
                {"id": "execute-publication", "type": "execute-publication", "config": {}},
                {"id": "verify-publication-execution", "type": "verify-publication-execution", "config": {}},
            ],
            "edges": [{"source": "execute-publication", "target": "verify-publication-execution", "relationship": "Fact"}],
        }
    )
}

PUBLICATION_BATCH_EXECUTION_GRAPHS = {
    "publication-batch-execute": GraphDefinition.from_dict(
        {
            "schemaVersion": 1,
            "graphId": "publication-batch-execute",
            "revision": 1,
            "nodes": [
                {"id": "execute-publication-batch", "type": "execute-publication-batch", "config": {}},
                {"id": "verify-publication-batch-execution", "type": "verify-publication-batch-execution", "config": {}},
            ],
            "edges": [
                {"source": "execute-publication-batch", "target": "verify-publication-batch-execution", "relationship": "Fact"}
            ],
        }
    )
}

YOUTUBE_CONNECT_GRAPHS = {
    "youtube-connect": GraphDefinition.from_dict(
        {
            "schemaVersion": 1,
            "graphId": "youtube-connect",
            "revision": 1,
            "nodes": [
                {"id": "connect-youtube", "type": "connect-youtube", "config": {}},
                {"id": "verify-youtube-credential", "type": "verify-youtube-credential", "config": {}},
            ],
            "edges": [{"source": "connect-youtube", "target": "verify-youtube-credential", "relationship": "Fact"}],
        }
    )
}

SOURCE_GRAPHS = {**INTAKE_GRAPHS, **TRANSCRIPTION_GRAPHS, **TRANSLATION_GRAPHS, **VOICE_GRAPHS, **LOCALIZATION_GRAPHS, **RELEASE_GRAPHS, **CREATOR_GRAPHS, **CREATOR_BATCH_GRAPHS}

ALL_WORKFLOW_GRAPHS = {
    "prepared-localization": PREPARED_FOLDER_GRAPH,
    **SOURCE_GRAPHS,
    **PUBLICATION_GRAPHS,
    **PUBLICATION_EXECUTION_GRAPHS,
    **PUBLICATION_BATCH_EXECUTION_GRAPHS,
    **YOUTUBE_CONNECT_GRAPHS,
    **CREATOR_CAMPAIGN_GRAPHS,
}

VIDEO_EXTENSIONS = frozenset({".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"})


class StudioApplication:
    def __init__(
        self,
        store: RunStore,
        engine: WorkflowEngine,
        *,
        allowed_roots: tuple[Path, ...],
    ) -> None:
        self.store = store
        self.engine = engine
        self.allowed_roots = tuple(Path(root).resolve() for root in allowed_roots if Path(root).exists())

    def handle(
        self,
        method: str,
        path: str,
        query: dict[str, list[str]],
        body: dict[str, Any] | None,
    ) -> tuple[int, dict[str, Any]]:
        try:
            if method == "GET" and path == "/api/v1/health":
                queue = self.store.queue_snapshot()
                return 200, {
                    "contractVersion": "1.0",
                    "database": "ready",
                    "activeWorkers": 1 if self.engine.active_run_id else 0,
                    "queuedRuns": queue["queuedRuns"],
                }
            if method == "GET" and path == "/api/v1/queue":
                return 200, {"contractVersion": "1.0", **self.store.queue_snapshot()}
            if method == "GET" and path == "/api/v1/capabilities":
                return 200, {"contractVersion": "1.0", "capabilities": self._capabilities()}
            if method == "GET" and path == "/api/v1/languages":
                return 200, {"contractVersion": "1.0", "languages": language_rows()}
            if method == "GET" and path == "/api/v1/translation-providers":
                return 200, {
                    "contractVersion": "1.0",
                    "providers": [
                        {"id": "nllb", "name": "NLLB (local)", "ready": True, "defaultModel": "facebook/nllb-200-distilled-600M"},
                        {"id": "deepseek", "name": "DeepSeek (cloud)", "ready": bool(os.environ.get("DEEPSEEK_API_KEY", "").strip()), "defaultModel": "deepseek-v4-flash", "credentialEnvironment": "DEEPSEEK_API_KEY"},
                    ],
                }
            if method == "GET" and path == "/api/v1/folders":
                return self._folders(query)
            if method == "GET" and path == "/api/v1/runs":
                return 200, {"runs": self.store.list_runs()}
            if method == "POST" and path == "/api/v1/runs":
                return self._create_run(body)
            prefix = "/api/v1/runs/"
            if path.startswith(prefix):
                suffix = path[len(prefix) :]
                if suffix.endswith("/creator-catalog") and method == "GET":
                    run_id = suffix[: -len("/creator-catalog")]
                    if not run_id or "/" in run_id:
                        raise ContractError("REJECTED_MALFORMED", "invalid creator catalog run ID")
                    return 200, project_creator_catalog(self.store.get_run(run_id))
                if "/" not in suffix and method == "GET":
                    return 200, self.store.get_run(suffix)
                if suffix.endswith("/start") and method == "POST":
                    self._validate_envelope(body, "CMD-RUN-START")
                    result = self.engine.start(suffix[: -len("/start")])
                    return self._command_response(result.result_class, result.value, accepted=True)
                if suffix.endswith("/cancel") and method == "POST":
                    self._validate_envelope(body, "CMD-RUN-CANCEL")
                    result = self.engine.cancel(suffix[: -len("/cancel")])
                    return self._command_response(result.result_class, result.value)
            return 404, {"resultClass": "REJECTED_NOT_FOUND", "path": path}
        except KeyError as error:
            return 404, {"resultClass": "REJECTED_NOT_FOUND", "detail": str(error)}
        except ContractError as error:
            status = 403 if error.code == "REJECTED_UNAUTHORIZED" else 400
            return status, {"resultClass": error.code, "detail": str(error)}
        except (TypeError, ValueError) as error:
            return 400, {"resultClass": "REJECTED_MALFORMED", "detail": str(error)}

    def _create_run(self, body: dict[str, Any] | None) -> tuple[int, dict[str, Any]]:
        envelope = self._validate_envelope(body, "CMD-RUN-CREATE")
        payload = envelope.get("payload")
        if not isinstance(payload, dict):
            raise ContractError("REJECTED_MALFORMED", "payload must be an object")
        template_id = str(payload.get("templateId", "prepared-localization"))
        if template_id in SOURCE_GRAPHS:
            return self._create_intake_run(envelope, payload, template_id)
        if template_id in CREATOR_CAMPAIGN_GRAPHS:
            return self._create_creator_campaign_run(envelope, payload, template_id)
        if template_id in PUBLICATION_GRAPHS:
            return self._create_publication_plan_run(envelope, payload, template_id)
        if template_id in PUBLICATION_EXECUTION_GRAPHS:
            return self._create_publication_execution_run(envelope, payload, template_id)
        if template_id in PUBLICATION_BATCH_EXECUTION_GRAPHS:
            return self._create_publication_batch_execution_run(envelope, payload, template_id)
        if template_id in YOUTUBE_CONNECT_GRAPHS:
            return self._create_youtube_connect_run(envelope, payload, template_id)
        if template_id != "prepared-localization":
            raise ContractError("REJECTED_MALFORMED", f"unknown templateId: {template_id}")
        source = Path(str(payload.get("sourceRoot", ""))).resolve()
        self._require_allowed(source)
        languages = payload.get("languages")
        platforms = payload.get("platforms")
        if not isinstance(languages, list) or not languages:
            raise ContractError("REJECTED_MALFORMED", "languages must be a non-empty list")
        if not isinstance(platforms, list) or not platforms:
            raise ContractError("REJECTED_MALFORMED", "platforms must be a non-empty list")
        parameters = {
            "sourceRoot": str(source),
            "languages": [str(value) for value in languages],
            "voice": str(payload.get("voice", "ru-RU-DmitryNeural")),
            "platforms": [str(value) for value in platforms],
        }
        result = self.store.create_run(
            CreateRun(
                operation_id=str(envelope["operationId"]),
                correlation_id=str(envelope["correlationId"]),
                graph=PREPARED_FOLDER_GRAPH,
                parameters=parameters,
            )
        )
        status = 201 if result.result_class == "COMPLETED" else 200
        if result.result_class == "REJECTED_CONFLICT":
            status = 409
        return status, {"resultClass": result.result_class, "value": result.value}

    def _create_creator_campaign_run(
        self, envelope: dict[str, Any], payload: dict[str, Any], template_id: str
    ) -> tuple[int, dict[str, Any]]:
        forbidden = {"creatorManifestPath", "creatorManifestSha256", "authenticationFile"}
        if forbidden.intersection(payload):
            raise ContractError("REJECTED_MALFORMED", "creator artifact paths are resolved by Studio")
        creator_run_id = str(payload.get("creatorRunId", "")).strip()
        if not creator_run_id:
            raise ContractError("REJECTED_MALFORMED", "creatorRunId is required")
        try:
            creator_run = self.store.get_run(creator_run_id)
        except KeyError as error:
            raise ContractError("REJECTED_NOT_FOUND", "creator discovery run does not exist") from error
        catalog = project_creator_catalog(creator_run)
        requested = payload.get("selectedVideoIds")
        if (
            not isinstance(requested, list)
            or not requested
            or not all(isinstance(value, str) and value.strip() for value in requested)
            or len(set(requested)) != len(requested)
        ):
            raise ContractError("REJECTED_MALFORMED", "selectedVideoIds must be a non-empty unique list")
        requested_set = set(requested)
        known = {item["id"] for item in catalog["items"]}
        if not requested_set.issubset(known):
            raise ContractError("REJECTED_MALFORMED", "selectedVideoIds contains an unknown creator video")
        selected = [item["id"] for item in catalog["items"] if item["id"] in requested_set]
        discovery_fact = next(
            step["result"]
            for step in creator_run["steps"]
            if step["nodeId"] == "discover-creator" and step["status"] == "COMPLETED"
        )
        languages = payload.get("targetLanguages")
        supported = set(SUPPORTED_LANGUAGE_LOCALES)
        if (
            not isinstance(languages, list)
            or not languages
            or len(set(languages)) != len(languages)
            or not all(isinstance(value, str) and value in supported for value in languages)
        ):
            raise ContractError("REJECTED_MALFORMED", "targetLanguages must be a unique supported list")
        voices = payload.get("targetVoices")
        if (
            not isinstance(voices, dict)
            or set(voices) != set(languages)
            or any(not isinstance(value, str) or not value.strip() for value in voices.values())
        ):
            raise ContractError("REJECTED_MALFORMED", "targetVoices must cover every selected language exactly")
        source_language = str(payload.get("sourceLanguage", "auto")).strip()
        asr_model = str(payload.get("asrModel", "small")).strip()
        asr_device = str(payload.get("asrDevice", "auto")).strip()
        asr_compute_type = str(payload.get("asrComputeType", "default")).strip()
        translation_provider = str(payload.get("translationProvider", "nllb")).strip().lower()
        default_translation_model = "deepseek-v4-flash" if translation_provider == "deepseek" else "facebook/nllb-200-distilled-600M"
        translation_model = str(payload.get("translationModel", default_translation_model)).strip()
        translation_device = str(payload.get("translationDevice", "auto")).strip()
        try:
            translation_batch_size = int(payload.get("translationBatchSize", 8))
            source_volume = float(payload.get("sourceVolume", 0.12))
        except (TypeError, ValueError) as error:
            raise ContractError("REJECTED_MALFORMED", "campaign numeric policy is invalid") from error
        if (
            not source_language
            or not asr_model
            or not asr_compute_type
            or translation_provider not in {"nllb", "deepseek"}
            or not translation_model
            or asr_device not in {"auto", "cpu", "cuda"}
            or translation_device not in {"auto", "cpu", "cuda"}
            or not 1 <= translation_batch_size <= 64
            or not 0 <= source_volume <= 1
        ):
            raise ContractError("REJECTED_MALFORMED", "campaign processing policy is invalid")
        if translation_provider == "deepseek" and not os.environ.get("DEEPSEEK_API_KEY", "").strip():
            raise ContractError("REJECTED_MALFORMED", "DeepSeek translation requires DEEPSEEK_API_KEY")
        parameters = {
            "templateId": template_id,
            "creatorRunId": creator_run_id,
            "creatorManifestPath": str(Path(discovery_fact["manifest"]).resolve()),
            "creatorManifestSha256": str(discovery_fact["manifestSha256"]),
            "selectedVideoIds": selected,
            "sourceLanguage": source_language,
            "asrModel": asr_model,
            "asrDevice": asr_device,
            "asrComputeType": asr_compute_type,
            "translationModel": translation_model,
            "translationProvider": translation_provider,
            "translationDevice": translation_device,
            "translationBatchSize": translation_batch_size,
            "targetLanguages": list(languages),
            "targetVoices": {language: voices[language].strip() for language in languages},
            "sourceVolume": source_volume,
            "authenticationFile": creator_run.get("parameters", {}).get("authenticationFile"),
        }
        result = self.store.create_run(
            CreateRun(
                operation_id=str(envelope["operationId"]),
                correlation_id=str(envelope["correlationId"]),
                graph=CREATOR_CAMPAIGN_GRAPHS[template_id],
                parameters=parameters,
            )
        )
        status = 201 if result.result_class == "COMPLETED" else 200
        if result.result_class == "REJECTED_CONFLICT":
            status = 409
        return status, {"resultClass": result.result_class, "value": result.value}

    def _create_publication_plan_run(self, envelope, payload, template_id):
        video = Path(str(payload.get("videoPath", ""))).resolve()
        metadata = Path(str(payload.get("metadataPath", ""))).resolve()
        self._require_allowed(video); self._require_allowed(metadata)
        if not video.is_file() or video.suffix.lower() not in VIDEO_EXTENSIONS:
            raise ContractError("REJECTED_NOT_FOUND", "publication video does not exist")
        if not metadata.is_file() or metadata.suffix.lower() != ".json":
            raise ContractError("REJECTED_NOT_FOUND", "publication metadata JSON does not exist")
        targets = payload.get("targetPlatforms")
        supported = {"youtube", "bilibili", "douyin", "tiktok"}
        if not isinstance(targets, list) or not targets or len(set(targets)) != len(targets) or not all(value in supported for value in targets):
            raise ContractError("REJECTED_MALFORMED", "targetPlatforms must be a unique supported list")
        account = str(payload.get("account", "")).strip()
        if not account:
            raise ContractError("REJECTED_MALFORMED", "publication account is required")
        if payload.get("public") is True:
            raise ContractError("REJECTED_MALFORMED", "browser publication planning is private/draft only")
        credential_ids = payload.get("credentialIds", {})
        if not isinstance(credential_ids, dict) or not set(credential_ids).issubset(targets) or not all(isinstance(value,str) and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}",value) for value in credential_ids.values()):
            raise ContractError("REJECTED_MALFORMED", "credentialIds must map selected platforms to valid credential IDs")
        result = self.store.create_run(CreateRun(operation_id=str(envelope["operationId"]),correlation_id=str(envelope["correlationId"]),graph=PUBLICATION_GRAPHS[template_id],parameters={"templateId":template_id,"videoPath":str(video),"metadataPath":str(metadata),"targetPlatforms":list(targets),"account":account,"credentialIds":dict(credential_ids),"public":False}))
        status=201 if result.result_class=="COMPLETED" else 200
        if result.result_class=="REJECTED_CONFLICT": status=409
        return status,{"resultClass":result.result_class,"value":result.value}

    def _create_publication_execution_run(self, envelope, payload, template_id):
        plan_run_id = str(payload.get("planRunId", "")).strip()
        confirmation = str(payload.get("confirmation", "")).strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", confirmation):
            raise ContractError("REJECTED_MALFORMED", "confirmation must be a SHA-256")
        try:
            plan_run = self.store.get_run(plan_run_id)
        except KeyError as error:
            raise ContractError("REJECTED_NOT_FOUND", "publication plan run does not exist") from error
        if plan_run["status"] != "COMPLETED" or plan_run["graph"].get("graphId") != "publication-plan":
            raise ContractError("REJECTED_MALFORMED", "planRunId must name a completed publication-plan run")
        if not any(step.get("nodeId") == "verify-publication-plan" and step.get("status") == "COMPLETED" for step in plan_run["steps"]):
            raise ContractError("REJECTED_MALFORMED", "publication plan run lacks a verified plan fact")
        committed = next((step.get("result") for step in plan_run["steps"] if step.get("nodeId") == "plan-publication" and step.get("status") == "COMPLETED"), None)
        if not isinstance(committed, dict):
            raise ContractError("REJECTED_MALFORMED", "publication plan fact is missing")
        plan = Path(str(committed.get("manifest", ""))).resolve()
        if not plan.is_file() or hashlib.sha256(plan.read_bytes()).hexdigest() != committed.get("manifestSha256") or confirmation != committed.get("manifestSha256"):
            raise ContractError("REJECTED_CONFLICT", "publication plan confirmation does not match the committed fact")
        try:
            value = json.loads(plan.read_text(encoding="utf-8-sig")); jobs = value["jobs"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
            raise ContractError("REJECTED_MALFORMED", "publication plan is invalid") from error
        if value.get("public") is not False or not jobs or not all(row.get("platform") == "youtube" and row.get("visibility") == "private-or-draft" and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", str(row.get("credentialId", ""))) for row in jobs):
            raise ContractError("REJECTED_MALFORMED", "browser execution requires credential-backed private YouTube jobs")
        vault = Path(str(payload.get("credentialVaultPath", ""))).resolve()
        if not vault.is_file() or not vault.is_relative_to(Path.home().resolve()):
            raise ContractError("REJECTED_MALFORMED", "credentialVaultPath must be an existing file inside the user home directory")
        parameters = {"templateId":template_id,"planRunId":plan_run_id,"planPath":str(plan),"confirmation":confirmation,"credentialVaultPath":str(vault)}
        result = self.store.create_run(CreateRun(operation_id=str(envelope["operationId"]),correlation_id=str(envelope["correlationId"]),graph=PUBLICATION_EXECUTION_GRAPHS[template_id],parameters=parameters))
        status=201 if result.result_class=="COMPLETED" else 200
        if result.result_class=="REJECTED_CONFLICT": status=409
        return status,{"resultClass":result.result_class,"value":result.value}

    def _create_youtube_connect_run(self, envelope, payload, template_id):
        client_config = Path(str(payload.get("clientConfigPath", ""))).resolve()
        self._require_allowed(client_config)
        if not client_config.is_file() or client_config.suffix.lower() != ".json":
            raise ContractError("REJECTED_NOT_FOUND", "Google desktop OAuth client JSON does not exist")
        vault = Path(str(payload.get("credentialVaultPath", ""))).resolve()
        home = Path.home().resolve()
        if vault.suffix.lower() != ".json" or not vault.is_relative_to(home):
            raise ContractError("REJECTED_MALFORMED", "credentialVaultPath must be a JSON path inside the user home directory")
        credential_id = str(payload.get("credentialId", "")).strip()
        label = str(payload.get("label", "")).strip()
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", credential_id):
            raise ContractError("REJECTED_MALFORMED", "credentialId is invalid")
        if not label or len(label) > 100:
            raise ContractError("REJECTED_MALFORMED", "label must contain 1 to 100 characters")
        parameters = {"templateId": template_id, "clientConfigPath": str(client_config), "credentialVaultPath": str(vault), "credentialId": credential_id, "label": label}
        result = self.store.create_run(CreateRun(operation_id=str(envelope["operationId"]), correlation_id=str(envelope["correlationId"]), graph=YOUTUBE_CONNECT_GRAPHS[template_id], parameters=parameters))
        status = 201 if result.result_class == "COMPLETED" else 200
        if result.result_class == "REJECTED_CONFLICT": status = 409
        return status, {"resultClass": result.result_class, "value": result.value}

    def _create_publication_batch_execution_run(self, envelope, payload, template_id):
        release_run_id = str(payload.get("releasePlanRunId", "")).strip()
        confirmation = str(payload.get("confirmation", "")).strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", confirmation):
            raise ContractError("REJECTED_MALFORMED", "confirmation must be a SHA-256")
        try:
            release_run = self.store.get_run(release_run_id)
        except KeyError as error:
            raise ContractError("REJECTED_NOT_FOUND", "release planning run does not exist") from error
        if release_run["status"] != "COMPLETED" or release_run["graph"].get("graphId") not in RELEASE_GRAPHS:
            raise ContractError("REJECTED_MALFORMED", "releasePlanRunId must name a completed Release planning run")
        if not any(
            step.get("nodeId") == "verify-publication-batch" and step.get("status") == "COMPLETED"
            for step in release_run["steps"]
        ):
            raise ContractError("REJECTED_MALFORMED", "Release planning run lacks a verified batch fact")
        committed = next(
            (
                step.get("result")
                for step in release_run["steps"]
                if step.get("nodeId") == "plan-publication-batch" and step.get("status") == "COMPLETED"
            ),
            None,
        )
        if not isinstance(committed, dict):
            raise ContractError("REJECTED_MALFORMED", "Publication Batch Plan fact is missing")
        plan = Path(str(committed.get("manifest", ""))).resolve()
        try:
            actual_sha = hashlib.sha256(plan.read_bytes()).hexdigest() if plan.is_file() else ""
        except OSError:
            actual_sha = ""
        if actual_sha != committed.get("manifestSha256") or confirmation != committed.get("manifestSha256"):
            raise ContractError("REJECTED_CONFLICT", "batch confirmation does not match the committed Release fact")
        try:
            value = json.loads(plan.read_text(encoding="utf-8-sig"))
            targets = value["targets"]
            items = value["items"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
            raise ContractError("REJECTED_MALFORMED", "Publication Batch Plan is invalid") from error
        valid_policy = (
            value.get("schemaVersion") == 1
            and value.get("public") is False
            and value.get("maximumActiveItems") == 1
            and isinstance(targets, list)
            and len(targets) == 1
            and isinstance(targets[0], dict)
            and targets[0].get("platform") == "youtube"
            and bool(str(targets[0].get("account", "")).strip())
            and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", str(targets[0].get("credentialId", ""))) is not None
            and isinstance(items, list)
            and bool(items)
            and value.get("totalJobCount") == len(items)
        )
        if not valid_policy:
            raise ContractError("REJECTED_MALFORMED", "browser batch execution requires one credential-backed private YouTube target")
        vault = Path(str(payload.get("credentialVaultPath", ""))).resolve()
        if not vault.is_file() or not vault.is_relative_to(Path.home().resolve()):
            raise ContractError("REJECTED_MALFORMED", "credentialVaultPath must be an existing file inside the user home directory")
        parameters = {
            "templateId": template_id,
            "releasePlanRunId": release_run_id,
            "batchPlanPath": str(plan),
            "confirmation": confirmation,
            "credentialVaultPath": str(vault),
        }
        result = self.store.create_run(
            CreateRun(
                operation_id=str(envelope["operationId"]),
                correlation_id=str(envelope["correlationId"]),
                graph=PUBLICATION_BATCH_EXECUTION_GRAPHS[template_id],
                parameters=parameters,
            )
        )
        status = 201 if result.result_class == "COMPLETED" else 200
        if result.result_class == "REJECTED_CONFLICT":
            status = 409
        return status, {"resultClass": result.result_class, "value": result.value}

    def _create_intake_run(
        self, envelope: dict[str, Any], payload: dict[str, Any], template_id: str
    ) -> tuple[int, dict[str, Any]]:
        folder_mode = template_id.startswith("folder-")
        creator_batch_mode = template_id in CREATOR_BATCH_GRAPHS
        release_mode = template_id in RELEASE_GRAPHS
        if folder_mode:
            source = Path(str(payload.get("sourceRoot", ""))).resolve()
            self._require_allowed(source)
            if not source.is_dir():
                raise ContractError("REJECTED_NOT_FOUND", f"folder does not exist: {source}")
            parameters = {
                "templateId": template_id,
                "sourceKind": "folder",
                "sourceRoot": str(source),
            }
        else:
            value = str(payload.get("sourceUrl", ""))
            parsed = urlparse(value)
            host = (parsed.hostname or "").lower()
            hosts = ("youtube.com", "youtu.be", "bilibili.com", "b23.tv", "douyin.com", "tiktok.com")
            if parsed.scheme != "https" or not any(
                host == suffix or host.endswith("." + suffix) for suffix in hosts
            ):
                raise ContractError("REJECTED_MALFORMED", "unsupported social source URL")
            parameters = {
                "templateId": template_id,
                "sourceKind": "url",
                "sourceUrl": value,
                "maxHeight": int(payload.get("maxHeight", 1080)),
            }
        if template_id in CREATOR_GRAPHS or creator_batch_mode:
            try:
                max_items = int(payload.get("maxItems", 0))
            except (TypeError, ValueError) as error:
                raise ContractError("REJECTED_MALFORMED", "maxItems must be zero or a positive integer") from error
            if not 0 <= max_items <= 10000:
                raise ContractError("REJECTED_MALFORMED", "maxItems must be between 0 and 10000")
            authentication = str(payload.get("authenticationFile", "")).strip()
            authentication_path = None
            if authentication:
                authentication_path = Path(authentication).resolve()
                home = Path.home().resolve()
                if not authentication_path.is_file() or not authentication_path.is_relative_to(home):
                    raise ContractError("REJECTED_MALFORMED", "authenticationFile must be an existing file inside the user home directory")
            parameters = {
                "templateId": template_id,
                "sourceKind": "creator-profile",
                "sourceUrl": value,
                "maxItems": max_items,
                "authenticationFile": str(authentication_path) if authentication_path else None,
            }
        if template_id in TRANSCRIPTION_GRAPHS or template_id in TRANSLATION_GRAPHS or template_id in VOICE_GRAPHS or template_id in LOCALIZATION_GRAPHS or release_mode or creator_batch_mode:
            source_language = str(payload.get("sourceLanguage", "auto")).strip()
            model = str(payload.get("asrModel", "small")).strip()
            device = str(payload.get("asrDevice", "auto")).strip()
            compute_type = str(payload.get("asrComputeType", "default")).strip()
            if not source_language or not model or not compute_type:
                raise ContractError("REJECTED_MALFORMED", "ASR policy values are required")
            if device not in {"auto", "cpu", "cuda"}:
                raise ContractError("REJECTED_MALFORMED", "unsupported ASR device")
            parameters.update(
                {
                    "sourceLanguage": source_language,
                    "asrModel": model,
                    "asrDevice": device,
                    "asrComputeType": compute_type,
                }
            )
        if template_id in TRANSLATION_GRAPHS or template_id in VOICE_GRAPHS or template_id in LOCALIZATION_GRAPHS or release_mode or creator_batch_mode:
            languages = payload.get("targetLanguages")
            supported = set(SUPPORTED_LANGUAGE_LOCALES)
            if (
                not isinstance(languages, list)
                or not languages
                or not all(isinstance(value, str) and value in supported for value in languages)
                or len(set(languages)) != len(languages)
            ):
                raise ContractError("REJECTED_MALFORMED", "targetLanguages must be a unique supported list")
            translation_provider = str(payload.get("translationProvider", "nllb")).strip().lower()
            default_translation_model = "deepseek-v4-flash" if translation_provider == "deepseek" else "facebook/nllb-200-distilled-600M"
            translation_model = str(payload.get("translationModel", default_translation_model)).strip()
            translation_device = str(payload.get("translationDevice", "auto")).strip()
            translation_batch_size = int(payload.get("translationBatchSize", 8))
            if translation_provider not in {"nllb", "deepseek"} or not translation_model or translation_device not in {"auto", "cpu", "cuda"}:
                raise ContractError("REJECTED_MALFORMED", "unsupported translation policy")
            if translation_provider == "deepseek" and not os.environ.get("DEEPSEEK_API_KEY", "").strip():
                raise ContractError("REJECTED_MALFORMED", "DeepSeek translation requires DEEPSEEK_API_KEY")
            if not 1 <= translation_batch_size <= 64:
                raise ContractError("REJECTED_MALFORMED", "translationBatchSize must be between 1 and 64")
            parameters.update(
                {
                    "targetLanguages": list(languages),
                    "translationProvider": translation_provider,
                    "translationModel": translation_model,
                    "translationDevice": translation_device,
                    "translationBatchSize": translation_batch_size,
                }
            )
        if template_id in VOICE_GRAPHS or template_id in LOCALIZATION_GRAPHS or release_mode or creator_batch_mode:
            voices = payload.get("targetVoices")
            if not isinstance(voices, dict) or set(voices) != set(parameters["targetLanguages"]) or any(not isinstance(value, str) or not value.strip() for value in voices.values()):
                raise ContractError("REJECTED_MALFORMED", "targetVoices must cover every selected language exactly")
            parameters["targetVoices"] = dict(voices)
        if template_id in LOCALIZATION_GRAPHS or release_mode or creator_batch_mode:
            try:
                source_volume = float(payload.get("sourceVolume", 0.12))
            except (TypeError, ValueError) as error:
                raise ContractError("REJECTED_MALFORMED", "sourceVolume must be a number between 0 and 1") from error
            if not 0 <= source_volume <= 1:
                raise ContractError("REJECTED_MALFORMED", "sourceVolume must be between 0 and 1")
            parameters["sourceVolume"] = source_volume
        if release_mode:
            metadata = Path(str(payload.get("metadataTemplatePath", ""))).resolve()
            self._require_allowed(metadata)
            if not metadata.is_file() or metadata.suffix.lower() != ".json":
                raise ContractError("REJECTED_NOT_FOUND", "publication metadata template JSON does not exist")
            targets = payload.get("targetPlatforms")
            supported_platforms = {"youtube", "bilibili", "douyin", "tiktok"}
            if (
                not isinstance(targets, list)
                or not targets
                or len(set(targets)) != len(targets)
                or not all(isinstance(value, str) and value in supported_platforms for value in targets)
            ):
                raise ContractError("REJECTED_MALFORMED", "targetPlatforms must be a unique supported list")
            accounts = payload.get("targetAccounts")
            if (
                not isinstance(accounts, dict)
                or set(accounts) != set(targets)
                or any(not isinstance(value, str) or not value.strip() or len(value.strip()) > 128 for value in accounts.values())
            ):
                raise ContractError("REJECTED_MALFORMED", "targetAccounts must exactly cover selected platforms")
            credential_ids = payload.get("credentialIds", {})
            if (
                not isinstance(credential_ids, dict)
                or not set(credential_ids).issubset(targets)
                or not all(
                    isinstance(value, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", value)
                    for value in credential_ids.values()
                )
            ):
                raise ContractError("REJECTED_MALFORMED", "credentialIds must map selected platforms to valid credential IDs")
            if payload.get("public") is True:
                raise ContractError("REJECTED_MALFORMED", "Release planning is private/draft only")
            parameters.update(
                {
                    "metadataTemplatePath": str(metadata),
                    "targetPlatforms": list(targets),
                    "targetAccounts": {platform: accounts[platform].strip() for platform in targets},
                    "credentialIds": {platform: credential_ids[platform] for platform in targets if platform in credential_ids},
                    "public": False,
                }
            )
        result = self.store.create_run(
            CreateRun(
                operation_id=str(envelope["operationId"]),
                correlation_id=str(envelope["correlationId"]),
                graph=SOURCE_GRAPHS[template_id],
                parameters=parameters,
            )
        )
        status = 201 if result.result_class == "COMPLETED" else 200
        if result.result_class == "REJECTED_CONFLICT":
            status = 409
        return status, {"resultClass": result.result_class, "value": result.value}

    @staticmethod
    def _validate_envelope(
        body: dict[str, Any] | None, contract_id: str
    ) -> dict[str, Any]:
        if not isinstance(body, dict):
            raise ContractError("REJECTED_MALFORMED", "JSON object required")
        if body.get("contractId") != contract_id or body.get("contractVersion") != "1.0":
            raise ContractError("REJECTED_VERSION", "unsupported contract")
        for field in ("operationId", "correlationId"):
            if not isinstance(body.get(field), str) or not body[field].strip():
                raise ContractError("REJECTED_MALFORMED", f"{field} is required")
        return body

    def _folders(self, query: dict[str, list[str]]) -> tuple[int, dict[str, Any]]:
        requested = query.get("path", [str(self.allowed_roots[0]) if self.allowed_roots else ""])[0]
        folder = Path(requested).resolve()
        self._require_allowed(folder)
        if not folder.is_dir():
            return 404, {"resultClass": "REJECTED_NOT_FOUND", "path": str(folder)}
        directories = [
            {"name": item.name, "path": str(item)}
            for item in sorted(folder.iterdir(), key=lambda value: value.name.casefold())
            if item.is_dir()
        ]
        video_count = sum(
            1 for item in folder.iterdir() if item.is_file() and item.suffix.lower() in VIDEO_EXTENSIONS
        )
        parent = folder.parent if folder != folder.parent and self._is_allowed(folder.parent) else None
        return 200, {
            "path": str(folder),
            "parent": str(parent) if parent else None,
            "directories": directories,
            "videoCount": video_count,
        }

    def _require_allowed(self, path: Path) -> None:
        if not self._is_allowed(path):
            raise ContractError("REJECTED_UNAUTHORIZED", f"path is outside allowed roots: {path}")

    def _is_allowed(self, path: Path) -> bool:
        return any(path == root or path.is_relative_to(root) for root in self.allowed_roots)

    @staticmethod
    def _command_response(
        result_class: str, value: dict[str, Any], *, accepted: bool = False
    ) -> tuple[int, dict[str, Any]]:
        status = 202 if accepted and result_class == "COMPLETED" else 200
        if result_class == "REJECTED_CONFLICT":
            status = 409
        elif result_class == "REJECTED_NOT_FOUND":
            status = 404
        return status, {"resultClass": result_class, "value": value}

    @staticmethod
    def _capabilities() -> list[dict[str, Any]]:
        return build_workflow_catalog(ALL_WORKFLOW_GRAPHS)
