"""Read-only projection of one verified Creator Discovery fact."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .contracts import ContractError


SUPPORTED_PLATFORMS = frozenset({"youtube", "bilibili", "douyin", "tiktok"})


def _committed_discovery(run: dict[str, Any]) -> dict[str, Any]:
    if run.get("graph", {}).get("graphId") != "creator-profile":
        raise ContractError("REJECTED_MALFORMED", "run is not a creator-profile discovery")
    if run.get("status") != "COMPLETED":
        raise ContractError("REJECTED_CONFLICT", "creator discovery is not completed")
    steps = run.get("steps")
    if not isinstance(steps, list):
        raise ContractError("REJECTED_MALFORMED", "creator discovery steps are invalid")
    verified = any(
        step.get("nodeId") == "verify-creator" and step.get("status") == "COMPLETED"
        for step in steps
        if isinstance(step, dict)
    )
    if not verified:
        raise ContractError("REJECTED_CONFLICT", "creator discovery has no verified manifest fact")
    result = next(
        (
            step.get("result")
            for step in steps
            if isinstance(step, dict)
            and step.get("nodeId") == "discover-creator"
            and step.get("status") == "COMPLETED"
        ),
        None,
    )
    if not isinstance(result, dict):
        raise ContractError("REJECTED_MALFORMED", "creator manifest fact is missing")
    return result


def _read_committed_manifest(result: dict[str, Any]) -> dict[str, Any]:
    path = Path(str(result.get("manifest", ""))).resolve()
    expected_sha = str(result.get("manifestSha256", ""))
    if not path.is_file():
        raise ContractError("REJECTED_NOT_FOUND", "committed creator manifest does not exist")
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise ContractError("REJECTED_NOT_FOUND", "committed creator manifest cannot be read") from error
    if len(expected_sha) != 64 or hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ContractError("REJECTED_CONFLICT", "creator manifest fingerprint does not match its fact")
    try:
        value = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ContractError("REJECTED_MALFORMED", "creator manifest is not valid JSON") from error
    if not isinstance(value, dict):
        raise ContractError("REJECTED_MALFORMED", "creator manifest must be an object")
    return value


def _project_items(value: dict[str, Any], platform: str) -> list[dict[str, Any]]:
    items = value.get("items")
    if not isinstance(items, list):
        raise ContractError("REJECTED_MALFORMED", "creator manifest items must be a list")
    projected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for expected_ordinal, item in enumerate(items, 1):
        if not isinstance(item, dict):
            raise ContractError("REJECTED_MALFORMED", "creator manifest item must be an object")
        identity = item.get("id")
        title = item.get("title")
        url = item.get("url")
        published_at = item.get("publishedAt")
        host = (urlparse(url).hostname or "").lower() if isinstance(url, str) else ""
        if (
            item.get("ordinal") != expected_ordinal
            or not isinstance(identity, str)
            or not identity.strip()
            or identity in seen
            or not isinstance(title, str)
            or not title.strip()
            or not isinstance(url, str)
            or urlparse(url).scheme != "https"
            or not host
            or (published_at is not None and not isinstance(published_at, int))
        ):
            raise ContractError("REJECTED_MALFORMED", "creator manifest item contract is invalid")
        seen.add(identity)
        projected.append(
            {
                "ordinal": expected_ordinal,
                "id": identity,
                "url": url,
                "title": title,
                "publishedAt": published_at,
                # Discovery does not download media or inspect embedded/source subtitles.
                "subtitleStatus": "UNKNOWN_ASR",
            }
        )
    return projected


def project_creator_catalog(run: dict[str, Any]) -> dict[str, Any]:
    """Project a browser-safe catalog from an immutable verified manifest fact."""

    value = _read_committed_manifest(_committed_discovery(run))
    platform = value.get("platform")
    creator = value.get("creator")
    requested_url = value.get("requestedUrl")
    source_kind = value.get("sourceKind", "profile")
    if (
        value.get("schemaVersion") != 1
        or platform not in SUPPORTED_PLATFORMS
        or not isinstance(requested_url, str)
        or not requested_url.strip()
        or source_kind not in {"profile", "video"}
        or not isinstance(creator, dict)
        or not isinstance(creator.get("id"), str)
        or not creator["id"].strip()
        or creator.get("name") is not None
        and not isinstance(creator.get("name"), str)
        or not isinstance(value.get("complete"), bool)
        or not isinstance(value.get("truncated"), bool)
    ):
        raise ContractError("REJECTED_MALFORMED", "creator manifest header contract is invalid")
    items = _project_items(value, platform)
    return {
        "schemaVersion": 1,
        "runId": str(run["runId"]),
        "platform": platform,
        "requestedUrl": requested_url,
        "sourceKind": source_kind,
        "creator": {"id": creator["id"], "name": creator.get("name")},
        "complete": value["complete"],
        "truncated": value["truncated"],
        "itemCount": len(items),
        "items": items,
    }
