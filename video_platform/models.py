from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Platform(StrEnum):
    YOUTUBE = "youtube"
    BILIBILI = "bilibili"
    DOUYIN = "douyin"
    TIKTOK = "tiktok"


@dataclass(frozen=True)
class ProcessResult:
    args: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class JobReceipt:
    platform: Platform
    operation: str
    status: str
    facts: dict[str, Any] = field(default_factory=dict)
    output_path: str | None = None
    error: str | None = None
