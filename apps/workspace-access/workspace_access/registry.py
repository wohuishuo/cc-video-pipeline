"""Atomic JSON registry for workspace identities and hashed bearer credentials."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
from typing import Any, Callable


SCHEMA_VERSION = 1
KNOWN_SCOPES = frozenset(
    {
        "runs:read",
        "runs:write",
        "artifacts:read",
        "publication:execute",
        "admin",
    }
)
IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


@dataclass(frozen=True)
class AccessResult:
    result_class: str
    value: dict[str, Any]


class RegistryError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


class AccessRegistry:
    def __init__(
        self,
        path: Path,
        *,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.path = Path(path).resolve()
        self.clock = clock

    def initialize_workspace(
        self,
        workspace_id: str,
        display_name: str,
        allowed_roots: list[Path],
    ) -> AccessResult:
        self._validate_identifier(workspace_id, "workspace ID")
        display_name = display_name.strip()
        if not display_name or len(display_name) > 128:
            raise RegistryError("REJECTED_MALFORMED", "display name is required")
        roots = self._canonical_roots(allowed_roots)
        registry = self._load()
        existing = self._workspace(registry, workspace_id)
        public = {
            "workspaceId": workspace_id,
            "displayName": display_name,
            "allowedRoots": roots,
        }
        if existing is not None:
            current = {key: existing[key] for key in public}
            result = "DUPLICATE_COMPLETED" if current == public else "REJECTED_CONFLICT"
            return AccessResult(result, current)
        registry["workspaces"].append({**public, "credentials": []})
        self._commit(registry)
        return AccessResult("COMPLETED", public)

    def issue_token(
        self,
        workspace_id: str,
        label: str,
        scopes: list[str],
        *,
        ttl: timedelta,
    ) -> AccessResult:
        self._validate_identifier(workspace_id, "workspace ID")
        label = label.strip()
        if not label or len(label) > 128:
            raise RegistryError("REJECTED_MALFORMED", "credential label is required")
        normalized_scopes = self._scopes(scopes)
        if ttl <= timedelta(0) or ttl > timedelta(days=365):
            raise RegistryError("REJECTED_MALFORMED", "TTL must be between 0 and 365 days")
        registry = self._load(require_exists=True)
        workspace = self._workspace(registry, workspace_id)
        if workspace is None:
            return AccessResult("REJECTED_NOT_FOUND", {"workspaceId": workspace_id})

        credential_id = secrets.token_hex(8)
        token = f"vgst_{credential_id}_{secrets.token_urlsafe(32)}"
        now = self.clock()
        expires_at = now + ttl
        workspace["credentials"].append(
            {
                "credentialId": credential_id,
                "label": label,
                "scopes": normalized_scopes,
                "tokenSha256": hashlib.sha256(token.encode("utf-8")).hexdigest(),
                "createdAt": _timestamp(now),
                "expiresAt": _timestamp(expires_at),
                "revokedAt": None,
            }
        )
        self._commit(registry)
        return AccessResult(
            "COMPLETED",
            {
                "workspaceId": workspace_id,
                "tokenId": credential_id,
                "label": label,
                "scopes": normalized_scopes,
                "expiresAt": _timestamp(expires_at),
                "token": token,
            },
        )

    def describe_workspace(self, workspace_id: str) -> AccessResult:
        self._validate_identifier(workspace_id, "workspace ID")
        registry = self._load(require_exists=True)
        workspace = self._workspace(registry, workspace_id)
        if workspace is None:
            return AccessResult("REJECTED_NOT_FOUND", {"workspaceId": workspace_id})
        return AccessResult(
            "COMPLETED",
            {
                "workspaceId": workspace["workspaceId"],
                "displayName": workspace["displayName"],
                "allowedRoots": list(workspace["allowedRoots"]),
            },
        )

    def authorize(self, token: str, workspace_id: str, required_scope: str) -> AccessResult:
        denied = AccessResult("REJECTED_UNAUTHORIZED", {"workspaceId": workspace_id})
        if required_scope not in KNOWN_SCOPES or not isinstance(token, str):
            return denied
        parts = token.split("_", 2)
        if len(parts) != 3 or parts[0] != "vgst" or not IDENTIFIER.fullmatch(workspace_id):
            return denied
        credential_id = parts[1]
        try:
            registry = self._load(require_exists=True)
        except RegistryError:
            return denied
        workspace = self._workspace(registry, workspace_id)
        if workspace is None:
            return denied
        credential = next(
            (
                item
                for item in workspace["credentials"]
                if item["credentialId"] == credential_id
            ),
            None,
        )
        if credential is None or credential["revokedAt"] is not None:
            return denied
        supplied_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(supplied_hash, credential["tokenSha256"]):
            return denied
        if self.clock() >= datetime.fromisoformat(credential["expiresAt"]):
            return denied
        if required_scope not in credential["scopes"] and "admin" not in credential["scopes"]:
            return denied
        return AccessResult(
            "AUTHORIZED",
            {
                "workspaceId": workspace_id,
                "credentialId": credential_id,
                "label": credential["label"],
                "scopes": credential["scopes"],
                "expiresAt": credential["expiresAt"],
            },
        )

    def revoke_token(self, workspace_id: str, credential_id: str) -> AccessResult:
        self._validate_identifier(workspace_id, "workspace ID")
        if not re.fullmatch(r"[0-9a-f]{16}", credential_id):
            raise RegistryError("REJECTED_MALFORMED", "invalid credential ID")
        registry = self._load(require_exists=True)
        workspace = self._workspace(registry, workspace_id)
        if workspace is None:
            return AccessResult("REJECTED_NOT_FOUND", {"workspaceId": workspace_id})
        credential = next(
            (
                item
                for item in workspace["credentials"]
                if item["credentialId"] == credential_id
            ),
            None,
        )
        if credential is None:
            return AccessResult(
                "REJECTED_NOT_FOUND",
                {"workspaceId": workspace_id, "credentialId": credential_id},
            )
        value = {"workspaceId": workspace_id, "credentialId": credential_id}
        if credential["revokedAt"] is not None:
            return AccessResult("DUPLICATE_COMPLETED", value)
        credential["revokedAt"] = _timestamp(self.clock())
        self._commit(registry)
        return AccessResult("COMPLETED", value)

    @staticmethod
    def _validate_identifier(value: str, label: str) -> None:
        if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
            raise RegistryError("REJECTED_MALFORMED", f"invalid {label}")

    @staticmethod
    def _canonical_roots(roots: list[Path]) -> list[str]:
        if not roots:
            raise RegistryError("REJECTED_MALFORMED", "at least one allowed root is required")
        result: list[str] = []
        for item in roots:
            root = Path(item).resolve()
            if not root.is_dir():
                raise RegistryError("REJECTED_NOT_FOUND", f"allowed root is not a directory: {root}")
            value = str(root)
            if value not in result:
                result.append(value)
        return sorted(result, key=str.casefold)

    @staticmethod
    def _scopes(scopes: list[str]) -> list[str]:
        normalized = sorted(set(scopes))
        if not normalized or any(scope not in KNOWN_SCOPES for scope in normalized):
            raise RegistryError("REJECTED_MALFORMED", "one or more scopes are unknown")
        return normalized

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
                raise RegistryError("REJECTED_NOT_FOUND", "access registry does not exist")
            return {"schemaVersion": SCHEMA_VERSION, "revision": 0, "workspaces": []}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RegistryError("REJECTED_MALFORMED", f"invalid access registry: {error}") from error
        if (
            not isinstance(value, dict)
            or value.get("schemaVersion") != SCHEMA_VERSION
            or not isinstance(value.get("revision"), int)
            or not isinstance(value.get("workspaces"), list)
        ):
            raise RegistryError("REJECTED_VERSION", "unsupported access registry")
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
