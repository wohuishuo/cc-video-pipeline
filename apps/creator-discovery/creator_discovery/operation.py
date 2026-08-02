"""Durable, idempotent profile pagination loop."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol

from .contracts import CreatorItem, DiscoveryError, DiscoveryPage, ProfileSpec


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.partial")
    partial.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(partial, path)


class ProfileEnumerator(Protocol):
    identity: str
    def enumerate(self, spec: ProfileSpec, cookies: Path | None, cursor: str | None, on_log: Callable[[str], None]) -> Iterable[DiscoveryPage]: ...


@dataclass(frozen=True)
class DiscoveryResult:
    result_class: str
    receipt_path: Path
    manifest_path: Path | None
    error: str | None = None


class DiscoveryOperation:
    def execute(self, spec: ProfileSpec, output_dir: Path, operation_id: str, *, enumerator: ProfileEnumerator, cookies: Path | None = None, on_log=None):
        if not operation_id.strip() or not enumerator.identity.strip():
            raise DiscoveryError("operation and adapter identity are required")
        output = Path(output_dir).resolve(); output.mkdir(parents=True, exist_ok=True)
        receipt_path = output / "discovery-receipt.json"; manifest_path = output / "creator-manifest.json"
        fingerprint = hashlib.sha256(_canonical({"schemaVersion":1,"profile":spec.to_public_dict(),"authMaterialSha256":spec.cookie_key,"adapter":enumerator.identity}).encode()).hexdigest()
        prior = self._read(receipt_path)
        if prior and (prior.get("operationId") != operation_id or prior.get("inputFingerprint") != fingerprint):
            return DiscoveryResult("REJECTED_CONFLICT", receipt_path, None, "operation input conflict")
        if prior and prior.get("resultClass") == "COMPLETED" and manifest_path.is_file() and _sha(manifest_path) == prior.get("manifestSha256"):
            return DiscoveryResult("DUPLICATE_COMPLETED", receipt_path, manifest_path)
        committed = [item for item in (prior or {}).get("items", []) if isinstance(item, dict)]
        cursor = (prior or {}).get("nextCursor")
        creator_id = (prior or {}).get("creator", {}).get("id")
        creator_name = (prior or {}).get("creator", {}).get("name")
        seen = {str(item.get("id")) for item in committed}; log = on_log or (lambda _line: None)
        maximum_active = 0; complete = False; truncated = False
        try:
            for page_number, page in enumerate(enumerator.enumerate(spec, cookies, cursor, log), 1):
                maximum_active = max(maximum_active, 1)
                creator_id = page.creator_id or creator_id; creator_name = page.creator_name or creator_name
                for item in page.items:
                    if item.id in seen: continue
                    if spec.max_items and len(committed) >= spec.max_items:
                        break
                    seen.add(item.id); committed.append(item.to_dict(len(committed) + 1))
                cursor = page.next_cursor
                reached_limit = bool(spec.max_items and len(committed) >= spec.max_items)
                complete = not page.has_more
                truncated = reached_limit and page.has_more
                self._checkpoint(receipt_path, operation_id, fingerprint, enumerator.identity, committed, cursor, creator_id, creator_name, maximum_active)
                log(f"Committed page {page_number}; {len(committed)} unique video(s)")
                if reached_limit or not page.has_more:
                    break
            if not committed:
                raise DiscoveryError("creator profile returned no videos")
            manifest = {"schemaVersion":1,"platform":spec.platform,"requestedUrl":spec.url,"creator":{"id":creator_id,"name":creator_name},"adapter":enumerator.identity,"maxItems":spec.max_items,"complete":complete,"truncated":truncated,"items":committed}
            _atomic(manifest_path, manifest); manifest_sha = _sha(manifest_path)
            self._checkpoint(receipt_path, operation_id, fingerprint, enumerator.identity, committed, cursor, creator_id, creator_name, maximum_active, result_class="COMPLETED", manifest=manifest_path, manifest_sha=manifest_sha)
            return DiscoveryResult("COMPLETED", receipt_path, manifest_path)
        except Exception as error:
            if manifest_path.exists(): manifest_path.unlink()
            self._checkpoint(receipt_path, operation_id, fingerprint, enumerator.identity, committed, cursor, creator_id, creator_name, maximum_active, result_class="FAILED", error=f"{type(error).__name__}: {error}"[-4000:])
            return DiscoveryResult("FAILED", receipt_path, None, str(error))

    @staticmethod
    def _read(path):
        try: return json.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else None
        except (OSError, json.JSONDecodeError): return None

    @staticmethod
    def _checkpoint(path, operation_id, fingerprint, adapter, items, cursor, creator_id, creator_name, maximum_active, *, result_class="RUNNING", manifest=None, manifest_sha=None, error=None):
        _atomic(path,{"schemaVersion":1,"operationId":operation_id,"inputFingerprint":fingerprint,"adapter":adapter,"resultClass":result_class,"creator":{"id":creator_id,"name":creator_name},"items":items,"itemCount":len(items),"nextCursor":cursor,"maximumActivePages":maximum_active,"manifest":str(manifest) if manifest else None,"manifestSha256":manifest_sha,"error":error})
