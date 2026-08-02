"""Atomic registry for deterministic, confined workspace storage namespaces."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Callable


SCHEMA_VERSION = 1
IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
NAMESPACE_KINDS = ("state", "artifacts", "temp")
MAX_QUOTA_BYTES = 2**63 - 1


@dataclass(frozen=True)
class StorageResult:
    result_class: str
    value: dict[str, Any]


class StorageRegistryError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


class StorageRegistry:
    def __init__(
        self,
        path: Path,
        *,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.path = Path(path).resolve()
        self.clock = clock

    def provision_workspace(
        self,
        workspace_id: str,
        storage_root: Path,
        *,
        quota_bytes: int,
    ) -> StorageResult:
        self._validate_workspace_id(workspace_id)
        self._validate_bytes(quota_bytes, "quota bytes", allow_zero=False)
        requested_root = Path(storage_root).resolve()
        registry = self._load()
        configured_root = registry.get("storageRoot")
        if configured_root is not None and Path(configured_root) != requested_root:
            raise StorageRegistryError(
                "REJECTED_CONFLICT", "registry is bound to a different storage root"
            )

        workspace_root = requested_root / "workspaces" / workspace_id
        roots = {
            "state": str(workspace_root / "state"),
            "artifacts": str(workspace_root / "artifacts"),
            "temp": str(workspace_root / "temp"),
        }
        public = {
            "workspaceId": workspace_id,
            "storageRoot": str(requested_root),
            "workspaceRoot": str(workspace_root),
            "roots": roots,
            "quotaBytes": quota_bytes,
        }
        existing = self._workspace(registry, workspace_id)
        if existing is not None:
            current = {key: existing[key] for key in public}
            if current != public:
                return StorageResult("REJECTED_CONFLICT", current)
            self._ensure_directories(requested_root, roots)
            return StorageResult("DUPLICATE_COMPLETED", current)

        self._ensure_directories(requested_root, roots)
        registry["storageRoot"] = str(requested_root)
        registry["workspaces"].append({**public, "createdAt": _timestamp(self.clock())})
        self._commit(registry)
        return StorageResult("COMPLETED", public)

    def describe_workspace(self, workspace_id: str) -> StorageResult:
        self._validate_workspace_id(workspace_id)
        registry = self._load(require_exists=True)
        workspace = self._workspace(registry, workspace_id)
        if workspace is None:
            return StorageResult("REJECTED_NOT_FOUND", {"workspaceId": workspace_id})
        return StorageResult(
            "COMPLETED",
            {
                "workspaceId": workspace["workspaceId"],
                "storageRoot": workspace["storageRoot"],
                "workspaceRoot": workspace["workspaceRoot"],
                "roots": dict(workspace["roots"]),
                "quotaBytes": workspace["quotaBytes"],
            },
        )

    def resolve_path(
        self,
        workspace_id: str,
        kind: str,
        relative_path: str,
    ) -> StorageResult:
        workspace, registry = self._required_workspace(workspace_id)
        if kind not in NAMESPACE_KINDS:
            raise StorageRegistryError("REJECTED_MALFORMED", "unknown namespace kind")
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise StorageRegistryError("REJECTED_PATH", "relative path is required")
        supplied = Path(relative_path)
        if supplied.is_absolute() or supplied.drive:
            raise StorageRegistryError("REJECTED_PATH", "absolute or drive paths are forbidden")
        root = self._verified_namespace_root(registry, workspace, kind)
        candidate = (root / supplied).resolve()
        if not candidate.is_relative_to(root):
            raise StorageRegistryError("REJECTED_PATH", "path escapes the workspace namespace")
        return StorageResult(
            "COMPLETED",
            {
                "workspaceId": workspace_id,
                "kind": kind,
                "relativePath": candidate.relative_to(root).as_posix(),
                "path": str(candidate),
            },
        )

    def check_capacity(self, workspace_id: str, *, required_bytes: int) -> StorageResult:
        self._validate_bytes(required_bytes, "required bytes", allow_zero=True)
        workspace, registry = self._required_workspace(workspace_id)
        workspace_root = self._verified_workspace_root(registry, workspace)
        usage = 0
        for candidate in workspace_root.rglob("*"):
            if candidate.is_symlink():
                raise StorageRegistryError(
                    "REJECTED_PATH", "workspace storage links are forbidden"
                )
            if not candidate.is_file():
                continue
            resolved = candidate.resolve()
            if not resolved.is_relative_to(workspace_root):
                raise StorageRegistryError(
                    "REJECTED_PATH", "workspace contains an escaping file link"
                )
            usage += resolved.stat().st_size
        quota = workspace["quotaBytes"]
        available = max(0, quota - usage)
        value = {
            "workspaceId": workspace_id,
            "quotaBytes": quota,
            "usageBytes": usage,
            "availableBytes": available,
            "requiredBytes": required_bytes,
        }
        result_class = "ALLOWED" if required_bytes <= available else "REJECTED_QUOTA"
        return StorageResult(result_class, value)

    def _required_workspace(
        self, workspace_id: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        self._validate_workspace_id(workspace_id)
        registry = self._load(require_exists=True)
        workspace = self._workspace(registry, workspace_id)
        if workspace is None:
            raise StorageRegistryError("REJECTED_NOT_FOUND", "workspace is not provisioned")
        return workspace, registry

    @staticmethod
    def _ensure_directories(storage_root: Path, roots: dict[str, str]) -> None:
        try:
            if storage_root.exists() and not storage_root.is_dir():
                raise StorageRegistryError("REJECTED_PATH", "storage root is not a directory")
            storage_root.mkdir(parents=True, exist_ok=True)
            for value in roots.values():
                Path(value).mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise StorageRegistryError(
                "REJECTED_PATH", f"could not create storage namespace: {error}"
            ) from error

    @staticmethod
    def _verified_storage_root(registry: dict[str, Any]) -> Path:
        declared = Path(registry["storageRoot"])
        resolved = declared.resolve()
        if resolved != declared:
            raise StorageRegistryError("REJECTED_PATH", "storage root was redirected")
        return resolved

    def _verified_workspace_root(
        self, registry: dict[str, Any], workspace: dict[str, Any]
    ) -> Path:
        storage_root = self._verified_storage_root(registry)
        declared = Path(workspace["workspaceRoot"])
        root = declared.resolve()
        if root != declared or not root.is_relative_to(storage_root):
            raise StorageRegistryError("REJECTED_PATH", "workspace root escaped storage")
        return root

    def _verified_namespace_root(
        self,
        registry: dict[str, Any],
        workspace: dict[str, Any],
        kind: str,
    ) -> Path:
        workspace_root = self._verified_workspace_root(registry, workspace)
        declared = Path(workspace["roots"][kind])
        root = declared.resolve()
        if root != declared or not root.is_relative_to(workspace_root):
            raise StorageRegistryError("REJECTED_PATH", "namespace root escaped workspace")
        return root

    @staticmethod
    def _validate_workspace_id(workspace_id: str) -> None:
        if not isinstance(workspace_id, str) or not IDENTIFIER.fullmatch(workspace_id):
            raise StorageRegistryError("REJECTED_MALFORMED", "invalid workspace ID")

    @staticmethod
    def _validate_bytes(value: int, label: str, *, allow_zero: bool) -> None:
        minimum = 0 if allow_zero else 1
        if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= MAX_QUOTA_BYTES:
            raise StorageRegistryError("REJECTED_MALFORMED", f"invalid {label}")

    @staticmethod
    def _workspace(registry: dict[str, Any], workspace_id: str) -> dict[str, Any] | None:
        return next(
            (
                workspace
                for workspace in registry["workspaces"]
                if workspace["workspaceId"] == workspace_id
            ),
            None,
        )

    def _load(self, *, require_exists: bool = False) -> dict[str, Any]:
        if not self.path.exists():
            if require_exists:
                raise StorageRegistryError("REJECTED_NOT_FOUND", "storage registry does not exist")
            return {
                "schemaVersion": SCHEMA_VERSION,
                "revision": 0,
                "storageRoot": None,
                "workspaces": [],
            }
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise StorageRegistryError(
                "REJECTED_MALFORMED", f"invalid storage registry: {error}"
            ) from error
        if (
            not isinstance(value, dict)
            or value.get("schemaVersion") != SCHEMA_VERSION
            or not isinstance(value.get("revision"), int)
            or not isinstance(value.get("storageRoot"), str)
            or not isinstance(value.get("workspaces"), list)
        ):
            raise StorageRegistryError("REJECTED_VERSION", "unsupported storage registry")
        return value

    def _commit(self, registry: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        registry["revision"] += 1
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(registry, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            temporary.unlink(missing_ok=True)
