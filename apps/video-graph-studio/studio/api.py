"""Versioned application API independent of the HTTP transport."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .contracts import ContractError, GraphDefinition
from .engine import WorkflowEngine
from .store import CreateRun, RunStore


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

SOURCE_GRAPHS = {**INTAKE_GRAPHS, **TRANSCRIPTION_GRAPHS, **TRANSLATION_GRAPHS}

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
                return 200, {
                    "contractVersion": "1.0",
                    "database": "ready",
                    "activeWorkers": 1 if self.engine.active_run_id else 0,
                }
            if method == "GET" and path == "/api/v1/capabilities":
                return 200, {"contractVersion": "1.0", "capabilities": self._capabilities()}
            if method == "GET" and path == "/api/v1/folders":
                return self._folders(query)
            if method == "GET" and path == "/api/v1/runs":
                return 200, {"runs": self.store.list_runs()}
            if method == "POST" and path == "/api/v1/runs":
                return self._create_run(body)
            prefix = "/api/v1/runs/"
            if path.startswith(prefix):
                suffix = path[len(prefix) :]
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

    def _create_intake_run(
        self, envelope: dict[str, Any], payload: dict[str, Any], template_id: str
    ) -> tuple[int, dict[str, Any]]:
        folder_mode = template_id.startswith("folder-")
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
        if template_id in TRANSCRIPTION_GRAPHS or template_id in TRANSLATION_GRAPHS:
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
        if template_id in TRANSLATION_GRAPHS:
            languages = payload.get("targetLanguages")
            supported = {"ru-RU", "en-US", "kk-KZ"}
            if (
                not isinstance(languages, list)
                or not languages
                or not all(isinstance(value, str) and value in supported for value in languages)
                or len(set(languages)) != len(languages)
            ):
                raise ContractError("REJECTED_MALFORMED", "targetLanguages must be a unique supported list")
            translation_model = str(payload.get("translationModel", "facebook/nllb-200-distilled-600M")).strip()
            translation_device = str(payload.get("translationDevice", "auto")).strip()
            translation_batch_size = int(payload.get("translationBatchSize", 8))
            if not translation_model or translation_device not in {"auto", "cpu", "cuda"}:
                raise ContractError("REJECTED_MALFORMED", "unsupported translation policy")
            if not 1 <= translation_batch_size <= 64:
                raise ContractError("REJECTED_MALFORMED", "translationBatchSize must be between 1 and 64")
            parameters.update(
                {
                    "targetLanguages": list(languages),
                    "translationModel": translation_model,
                    "translationDevice": translation_device,
                    "translationBatchSize": translation_batch_size,
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
        return [
            {
                "type": "prepared-folder",
                "title": "Prepared folder",
                "kind": "Query",
                "deliveryLevel": "DOMAIN_VERIFIED",
            },
            {
                "type": "edge-localize",
                "title": "Edge localization",
                "kind": "Adapter",
                "deliveryLevel": "IMPLEMENTED",
            },
            {
                "type": "verify-output",
                "title": "Verify outputs",
                "kind": "Policy",
                "deliveryLevel": "DOMAIN_VERIFIED",
            },
        ]
