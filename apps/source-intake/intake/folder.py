"""Deterministic folder discovery strategy."""

from __future__ import annotations

import hashlib
from pathlib import Path

from .contracts import IntakeError, MediaEntry, SourceManifest, SourceSpec, SUPPORTED_EXTENSIONS


def discover_folder(spec: SourceSpec) -> SourceManifest:
    if spec.kind != "folder":
        raise IntakeError("SOURCE_KIND_MISMATCH", "folder discovery requires a folder source")
    root = Path(spec.value).resolve()
    entries: list[MediaEntry] = []
    candidates = sorted(root.rglob("*"), key=lambda path: path.as_posix().casefold())
    for candidate in candidates:
        if not candidate.is_file() or candidate.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        resolved = candidate.resolve()
        if not resolved.is_relative_to(root):
            raise IntakeError("PATH_ESCAPE", f"media resolves outside source root: {candidate}")
        stat = resolved.stat()
        relative = resolved.relative_to(root).as_posix()
        identity = hashlib.sha256(
            f"{relative.casefold()}\0{stat.st_size}\0{stat.st_mtime_ns}".encode("utf-8")
        ).hexdigest()
        entries.append(MediaEntry(identity, str(resolved), stat.st_size, resolved.suffix.lower()))
    if not entries:
        raise IntakeError("EMPTY_SOURCE", f"no supported video files found under {root}")
    return SourceManifest("folder", {"root": str(root)}, tuple(entries))

