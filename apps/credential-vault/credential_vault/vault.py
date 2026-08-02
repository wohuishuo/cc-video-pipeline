"""Atomic, redacted registry for locally protected credentials."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import hmac
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Callable, Protocol

from .dpapi import DpapiCurrentUserCipher, DpapiError


SCHEMA_VERSION = 1
IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


class Cipher(Protocol):
    def protect(self, plaintext: bytes, context: bytes) -> bytes: ...
    def unprotect(self, ciphertext: bytes, context: bytes) -> bytes: ...


@dataclass(frozen=True)
class VaultResult:
    result_class: str
    value: dict[str, Any]


class VaultError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


class CredentialVault:
    def __init__(
        self,
        path: Path,
        *,
        cipher: Cipher | None = None,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.path = Path(path).resolve()
        try:
            self.cipher = cipher or DpapiCurrentUserCipher()
        except DpapiError as error:
            raise VaultError("REJECTED_PLATFORM", str(error)) from error
        self.clock = clock

    def put(
        self, credential_id: str, provider: str, label: str, secret: str
    ) -> VaultResult:
        self._validate_metadata(credential_id, provider, label)
        secret_bytes = self._secret_bytes(secret)
        registry = self._load()
        existing = self._record(registry, credential_id)
        if existing is not None:
            if existing["status"] != "ACTIVE":
                return VaultResult("REJECTED_CONFLICT", self._public(existing))
            same_metadata = (
                existing["provider"] == provider and existing["label"] == label
            )
            same_secret = same_metadata and hmac.compare_digest(
                self._decrypt(existing), secret
            )
            result_class = (
                "DUPLICATE_COMPLETED" if same_metadata and same_secret else "REJECTED_CONFLICT"
            )
            return VaultResult(result_class, self._public(existing))

        now = _timestamp(self.clock())
        record = {
            "credentialId": credential_id,
            "provider": provider,
            "label": label,
            "status": "ACTIVE",
            "ciphertext": self._protect(credential_id, secret_bytes),
            "createdAt": now,
            "updatedAt": now,
            "revokedAt": None,
        }
        registry["records"].append(record)
        self._commit(registry)
        return VaultResult("COMPLETED", self._public(record))

    def rotate(self, credential_id: str, secret: str) -> VaultResult:
        registry = self._load(require_exists=True)
        record = self._required_record(registry, credential_id)
        if record["status"] != "ACTIVE":
            raise VaultError("REJECTED_REVOKED", "credential is revoked")
        if hmac.compare_digest(self._decrypt(record), secret):
            return VaultResult("DUPLICATE_COMPLETED", self._public(record))
        record["ciphertext"] = self._protect(
            credential_id, self._secret_bytes(secret)
        )
        record["updatedAt"] = _timestamp(self.clock())
        self._commit(registry)
        return VaultResult("COMPLETED", self._public(record))

    def describe(self, credential_id: str) -> VaultResult:
        registry = self._load(require_exists=True)
        return VaultResult(
            "COMPLETED", self._public(self._required_record(registry, credential_id))
        )

    def revoke(self, credential_id: str) -> VaultResult:
        registry = self._load(require_exists=True)
        record = self._required_record(registry, credential_id)
        if record["status"] == "REVOKED":
            return VaultResult("DUPLICATE_COMPLETED", self._public(record))
        now = _timestamp(self.clock())
        record["status"] = "REVOKED"
        record["ciphertext"] = None
        record["updatedAt"] = now
        record["revokedAt"] = now
        self._commit(registry)
        return VaultResult("COMPLETED", self._public(record))

    def resolve_secret(self, credential_id: str) -> str:
        registry = self._load(require_exists=True)
        record = self._required_record(registry, credential_id)
        if record["status"] != "ACTIVE":
            raise VaultError("REJECTED_REVOKED", "credential is revoked")
        return self._decrypt(record)

    def _protect(self, credential_id: str, secret: bytes) -> str:
        try:
            protected = self.cipher.protect(secret, self._context(credential_id))
        except (DpapiError, OSError, ValueError) as error:
            raise VaultError("REJECTED_CIPHERTEXT", f"could not protect secret: {error}") from error
        return base64.b64encode(protected).decode("ascii")

    def _decrypt(self, record: dict[str, Any]) -> str:
        ciphertext = record.get("ciphertext")
        if not isinstance(ciphertext, str):
            raise VaultError("REJECTED_REVOKED", "credential has no active ciphertext")
        try:
            protected = base64.b64decode(ciphertext, validate=True)
            plaintext = self.cipher.unprotect(
                protected, self._context(record["credentialId"])
            )
            secret = plaintext.decode("utf-8")
        except VaultError:
            raise
        except (DpapiError, OSError, ValueError, UnicodeDecodeError) as error:
            raise VaultError("REJECTED_CIPHERTEXT", f"could not unprotect secret: {error}") from error
        if not secret:
            raise VaultError("REJECTED_CIPHERTEXT", "decrypted secret is empty")
        return secret

    @staticmethod
    def _context(credential_id: str) -> bytes:
        return f"credential-vault:v1:{credential_id}".encode("utf-8")

    @staticmethod
    def _secret_bytes(secret: str) -> bytes:
        if not isinstance(secret, str) or not secret:
            raise VaultError("REJECTED_SECRET", "secret must not be empty")
        if len(secret.encode("utf-8")) > 1_048_576:
            raise VaultError("REJECTED_SECRET", "secret exceeds one MiB")
        return secret.encode("utf-8")

    @staticmethod
    def _validate_metadata(credential_id: str, provider: str, label: str) -> None:
        if not isinstance(credential_id, str) or not IDENTIFIER.fullmatch(credential_id):
            raise VaultError("REJECTED_MALFORMED", "invalid credential ID")
        if not isinstance(provider, str) or not IDENTIFIER.fullmatch(provider):
            raise VaultError("REJECTED_MALFORMED", "invalid provider")
        if (
            not isinstance(label, str)
            or not 1 <= len(label) <= 200
            or any(ord(character) < 32 for character in label)
        ):
            raise VaultError("REJECTED_MALFORMED", "invalid label")

    def _required_record(
        self, registry: dict[str, Any], credential_id: str
    ) -> dict[str, Any]:
        if not isinstance(credential_id, str) or not IDENTIFIER.fullmatch(credential_id):
            raise VaultError("REJECTED_MALFORMED", "invalid credential ID")
        record = self._record(registry, credential_id)
        if record is None:
            raise VaultError("REJECTED_NOT_FOUND", "credential does not exist")
        return record

    @staticmethod
    def _record(registry: dict[str, Any], credential_id: str) -> dict[str, Any] | None:
        return next(
            (item for item in registry["records"] if item["credentialId"] == credential_id),
            None,
        )

    @staticmethod
    def _public(record: dict[str, Any]) -> dict[str, Any]:
        return {
            key: record[key]
            for key in (
                "credentialId",
                "provider",
                "label",
                "status",
                "createdAt",
                "updatedAt",
                "revokedAt",
            )
        }

    def _load(self, *, require_exists: bool = False) -> dict[str, Any]:
        if not self.path.exists():
            if require_exists:
                raise VaultError("REJECTED_NOT_FOUND", "credential vault does not exist")
            return {"schemaVersion": SCHEMA_VERSION, "revision": 0, "records": []}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise VaultError("REJECTED_MALFORMED", f"invalid credential vault: {error}") from error
        if (
            not isinstance(value, dict)
            or value.get("schemaVersion") != SCHEMA_VERSION
            or not isinstance(value.get("revision"), int)
            or not isinstance(value.get("records"), list)
        ):
            raise VaultError("REJECTED_VERSION", "unsupported credential vault")
        seen: set[str] = set()
        for record in value["records"]:
            if not self._valid_record(record) or record["credentialId"] in seen:
                raise VaultError("REJECTED_MALFORMED", "invalid credential record")
            seen.add(record["credentialId"])
        return value

    @staticmethod
    def _valid_record(record: Any) -> bool:
        required = {
            "credentialId", "provider", "label", "status", "ciphertext",
            "createdAt", "updatedAt", "revokedAt",
        }
        return (
            isinstance(record, dict)
            and set(record) == required
            and isinstance(record.get("credentialId"), str)
            and bool(IDENTIFIER.fullmatch(record["credentialId"]))
            and isinstance(record.get("provider"), str)
            and bool(IDENTIFIER.fullmatch(record["provider"]))
            and isinstance(record.get("label"), str)
            and 1 <= len(record["label"]) <= 200
            and not any(ord(character) < 32 for character in record["label"])
            and record.get("status") in {"ACTIVE", "REVOKED"}
            and (
                isinstance(record.get("ciphertext"), str)
                if record.get("status") == "ACTIVE"
                else record.get("ciphertext") is None
            )
            and isinstance(record.get("createdAt"), str)
            and isinstance(record.get("updatedAt"), str)
            and (record.get("revokedAt") is None or isinstance(record.get("revokedAt"), str))
            and (
                record.get("revokedAt") is None
                if record.get("status") == "ACTIVE"
                else isinstance(record.get("revokedAt"), str)
            )
        )

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
