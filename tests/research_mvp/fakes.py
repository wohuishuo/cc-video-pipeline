from pathlib import Path

from research_mvp.models import EvidenceItem, SourceRef


class FakeConnector:
    def __init__(self, source: SourceRef):
        self.source = source

    def resolve(self, raw_source: str) -> SourceRef:
        return self.source

    def facts(self, source: SourceRef) -> dict[str, object]:
        return {"title": "Fixture video", "duration_seconds": 12}


class FakeCollector:
    def __init__(self, *, gaps=(), error: Exception | None = None):
        self.gaps = tuple(gaps)
        self.error = error

    def collect(self, source: SourceRef, workspace: Path):
        if self.error:
            raise self.error
        workspace.mkdir(parents=True, exist_ok=True)
        transcript = workspace / "transcript.json"
        transcript.write_text('{"segments": []}\n', encoding="utf-8")
        return (
            (
                EvidenceItem(
                    "transcript", str(transcript), {"adapter": "fake"}
                ),
            ),
            self.gaps,
        )
