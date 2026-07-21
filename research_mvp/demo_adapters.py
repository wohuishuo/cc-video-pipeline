from hashlib import sha256
from pathlib import Path

from .models import EvidenceItem, SourceRef


class DemoConnector:
    def resolve(self, raw_source: str) -> SourceRef:
        if not raw_source.startswith("demo:") or not raw_source[5:]:
            raise ValueError("demo connector requires demo:<id>")
        source_id = raw_source[5:]
        return SourceRef("demo", source_id, f"demo://{source_id}")

    def facts(self, source: SourceRef) -> dict[str, object]:
        return {
            "title": f"Demo {source.source_id}",
            "duration_seconds": 12,
        }


class DemoEvidenceCollector:
    def collect(self, source: SourceRef, workspace: Path):
        workspace.mkdir(parents=True, exist_ok=True)
        transcript = workspace / "transcript.json"
        content = '{"language":"zh","segments":[]}\n'
        transcript.write_text(content, encoding="utf-8")
        digest = sha256(content.encode("utf-8")).hexdigest()
        evidence = EvidenceItem(
            kind="transcript",
            locator=str(transcript.resolve()),
            provenance={"adapter": "demo", "sha256": digest},
        )
        return (evidence,), ("visual_evidence_unavailable",)
