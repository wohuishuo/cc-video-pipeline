"""Read-only projection of committed workflow results for the Studio UI."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON fact is not an object: {path}")
    return value


def _committed_json(path_value: Any, expected_sha: Any) -> tuple[Path, dict[str, Any]]:
    path = Path(str(path_value or "")).resolve()
    expected = str(expected_sha or "")
    if not path.is_file() or len(expected) != 64 or _sha256(path) != expected:
        raise ValueError(f"Committed fact fingerprint mismatch: {path}")
    return path, _json(path)


def _within(path: Path, roots: Iterable[Path]) -> bool:
    return any(path == root or path.is_relative_to(root) for root in roots)


def _seconds(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _elapsed(run: dict[str, Any]) -> float | None:
    start = _seconds(run.get("createdAt"))
    end = _seconds(run.get("updatedAt"))
    if start is None or end is None:
        return None
    return max(0.0, round((end - start).total_seconds(), 3))


def _phase_durations(logs: list[dict[str, Any]]) -> dict[str, float]:
    starts: dict[tuple[str, str], datetime] = {}
    totals: dict[str, float] = {}
    for row in sorted(logs, key=lambda value: int(value.get("sequence", 0))):
        try:
            event = json.loads(str(row.get("message", "")))
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(event, dict) or event.get("event") != "creator_phase":
            continue
        phase = str(event.get("phase", "")).strip()
        item = event.get("item") if isinstance(event.get("item"), dict) else {}
        item_id = str(item.get("id", "")).strip()
        at = _seconds(row.get("created_at") or row.get("createdAt"))
        if not phase or at is None:
            continue
        key = (phase, item_id)
        if event.get("status") == "RUNNING" and key not in starts:
            starts[key] = at
        elif event.get("status") == "COMPLETED" and key in starts:
            totals[phase] = totals.get(phase, 0.0) + max(0.0, (at - starts.pop(key)).total_seconds())
    return {key: round(value, 3) for key, value in totals.items()}


def _usage_from_localization(value: dict[str, Any]) -> tuple[Path | None, dict[str, int] | None]:
    try:
        translation_path, _ = _committed_json(
            value.get("translationManifest"), value.get("translationManifestSha256")
        )
        receipt_path = translation_path.with_name("translation-receipt.json")
        receipt = _json(receipt_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return None, None
    totals = {"promptTokens": 0, "completionTokens": 0, "totalTokens": 0}
    reported = False
    for row in receipt.get("items", []):
        usage = row.get("usage") if isinstance(row, dict) else None
        values = [usage.get(key) for key in totals] if isinstance(usage, dict) else []
        if len(values) == 3 and all(type(item) is int and item >= 0 for item in values):
            reported = True
            for key in totals:
                totals[key] += usage[key]
    return receipt_path, totals if reported else None


def _video_id(run_id: str, source_item_id: str, derivative: dict[str, Any]) -> str:
    value = "\0".join(
        (
            run_id,
            source_item_id,
            str(derivative.get("targetLanguage", "")),
            str(derivative.get("mediaId", "")),
            str(derivative.get("path", "")),
        )
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _unavailable(run_id: str, source_item_id: str, title: str, error: str) -> dict[str, Any]:
    identity = hashlib.sha256(f"{run_id}\0{source_item_id}\0unavailable".encode()).hexdigest()[:24]
    return {
        "id": identity,
        "available": False,
        "sourceItemId": source_item_id,
        "title": title,
        "error": error,
    }


def project_run_results(
    run: dict[str, Any], *, allowed_roots: Iterable[Path] = ()
) -> dict[str, Any]:
    """Project verified result facts without changing workflow-owned manifests."""
    roots = tuple(Path(root).resolve() for root in allowed_roots)
    result: dict[str, Any] = {
        "status": str(run.get("status", "UNKNOWN")),
        "elapsedSeconds": _elapsed(run),
        "outputRoot": None,
        "totalBytes": 0,
        "reportedUsage": None,
        "phaseDurations": _phase_durations(run.get("logs", [])),
        "videos": [],
        "warnings": [],
    }
    step = next(
        (
            row
            for row in run.get("steps", [])
            if row.get("nodeId") == "localize-creator-batch"
            and row.get("status") == "COMPLETED"
            and isinstance(row.get("result"), dict)
        ),
        None,
    )
    if step is None:
        localization_step = next(
            (
                row
                for row in run.get("steps", [])
                if row.get("nodeId") == "localize-video"
                and row.get("status") == "COMPLETED"
                and isinstance(row.get("result"), dict)
            ),
            None,
        )
        if localization_step is None:
            result["warnings"].append("No completed Localization result is available")
            return result
        try:
            localization_path, _ = _committed_json(
                localization_step["result"].get("manifest"),
                localization_step["result"].get("manifestSha256"),
            )
        except (OSError, ValueError, json.JSONDecodeError) as error:
            result["warnings"].append(str(error))
            return result
        result["outputRoot"] = str(localization_path.parent)
        batch_path = localization_path
        batch = {
            "items": [
                {
                    "id": "",
                    "localizationManifest": str(localization_path),
                    "localizationManifestSha256": _sha256(localization_path),
                }
            ]
        }
    else:
        try:
            batch_path, batch = _committed_json(
                step["result"].get("manifest"), step["result"].get("manifestSha256")
            )
        except (OSError, ValueError, json.JSONDecodeError) as error:
            result["warnings"].append(str(error))
            return result
        result["outputRoot"] = str(batch_path.parent)

    titles: dict[str, str] = {}
    if batch.get("creatorManifest"):
        try:
            _, creator = _committed_json(
                batch.get("creatorManifest"), batch.get("creatorManifestSha256")
            )
            titles = {
                str(row.get("id")): str(row.get("title") or row.get("id"))
                for row in creator.get("items", [])
                if isinstance(row, dict) and row.get("id") is not None
            }
        except (OSError, ValueError, json.JSONDecodeError) as error:
            result["warnings"].append(str(error))

    usage_receipts: set[Path] = set()
    usage_total = {"promptTokens": 0, "completionTokens": 0, "totalTokens": 0}
    for item in batch.get("items", []):
        if not isinstance(item, dict):
            continue
        source_item_id = str(item.get("id", ""))
        title = titles.get(source_item_id, source_item_id)
        try:
            _, localization = _committed_json(
                item.get("localizationManifest"), item.get("localizationManifestSha256")
            )
        except (OSError, ValueError, json.JSONDecodeError) as error:
            result["videos"].append(_unavailable(str(run.get("runId", "")), source_item_id, title, str(error)))
            continue
        receipt_path, usage = _usage_from_localization(localization)
        if receipt_path is not None and receipt_path not in usage_receipts and usage is not None:
            usage_receipts.add(receipt_path)
            for key in usage_total:
                usage_total[key] += usage[key]
        derivatives = localization.get("derivatives")
        if not isinstance(derivatives, list) or not derivatives:
            result["videos"].append(_unavailable(str(run.get("runId", "")), source_item_id, title, "Localization Manifest has no derivatives"))
            continue
        for derivative in derivatives:
            if not isinstance(derivative, dict):
                continue
            resolved_source_id = source_item_id or str(derivative.get("mediaId", ""))
            resolved_title = title or Path(str(derivative.get("path", ""))).stem or resolved_source_id
            media_id = _video_id(str(run.get("runId", "")), resolved_source_id, derivative)
            try:
                path = Path(str(derivative["path"])).resolve()
                size = int(derivative["size"])
                if not roots or not _within(path, roots):
                    raise ValueError(f"Result path is outside allowed roots: {path}")
                if (
                    not path.is_file()
                    or path.stat().st_size != size
                    or _sha256(path) != str(derivative.get("sha256", ""))
                ):
                    raise ValueError(f"Result fingerprint mismatch: {path}")
                row = {
                    "id": media_id,
                    "available": True,
                    "sourceItemId": resolved_source_id,
                    "title": resolved_title,
                    "targetLanguage": str(derivative["targetLanguage"]),
                    "mediaId": str(derivative["mediaId"]),
                    "path": str(path),
                    "size": size,
                    "duration": float(derivative["duration"]),
                    "width": int(derivative["width"]),
                    "height": int(derivative["height"]),
                    "videoCodec": str(derivative["videoCodec"]),
                    "audioCodec": str(derivative["audioCodec"]),
                }
                result["videos"].append(row)
                result["totalBytes"] += size
            except (KeyError, OSError, TypeError, ValueError) as error:
                result["videos"].append(
                    {
                        "id": media_id,
                        "available": False,
                        "sourceItemId": resolved_source_id,
                        "title": resolved_title,
                        "targetLanguage": str(derivative.get("targetLanguage", "")),
                        "mediaId": str(derivative.get("mediaId", "")),
                        "error": str(error),
                    }
                )
    if usage_receipts:
        result["reportedUsage"] = usage_total
    return result
