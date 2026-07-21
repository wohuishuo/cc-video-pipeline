from pathlib import Path
from typing import Protocol

from .models import EvidenceItem, SourceRef


class SourceConnector(Protocol):
    def resolve(self, raw_source: str) -> SourceRef: ...

    def facts(self, source: SourceRef) -> dict[str, object]: ...


class EvidenceCollector(Protocol):
    def collect(
        self, source: SourceRef, workspace: Path
    ) -> tuple[tuple[EvidenceItem, ...], tuple[str, ...]]: ...
