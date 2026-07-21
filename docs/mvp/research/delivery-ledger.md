# Research MVP Delivery Ledger

level: `DOMAIN_VERIFIED`

present-evidence:

- Command: `python -m unittest discover -s tests/research_mvp -t . -v`; artifact: focused domain, repository, lifecycle, and CLI contract suite; result: 12 tests passed; date: 2026-07-21.
- Command: `python -m research_mvp --workspace <temporary-path> create demo:evidence`; artifact: domain end-to-end dossier; result: committed `complete_with_gaps` dossier with provenance and explicit visual gap; date: 2026-07-21.
- Command: `python -m research_mvp --workspace <same-path> show bdea1263b6ff5aae5439`; artifact: real adjacent integration between `ResearchService` and `FileResearchRepository`; result: reloaded the same committed dossier; date: 2026-07-21.
- Command: `python check_gitignore.py`; artifact: staged-file safety audit; result: zero sensitive files; date: 2026-07-21.

missing-evidence:

- Real local-file source adjacent integration.
- FFmpeg-derived evidence and transcription evidence.
- Bilibili/YouTube source resolution and authentication.
- Multi-process concurrency, restart/crash recovery, durability, scale, monitoring, and operations.

substitutes:

- `DemoConnector` substitutes for platform source connectors.
- `DemoEvidenceCollector` and generated transcript substitute for media, visual, and transcription evidence adapters.
- Temporary filesystem workspace substitutes for an operational artifact store.

decision-gates:

- Real platform connector and authentication policy.
- Visual evidence selection policy.
- Transcription engine policy.

supported-claims:

- `DOMAIN_VERIFIED`: stable source identity, research lifecycle, atomic dossier commit, explicit gaps, idempotent create, failure persistence, retry, and CLI domain loop pass with substitute source/evidence adapters and a real filesystem repository.

forbidden-claims:

- Platform integrated.
- Legacy pipeline replaced.
- Bilibili login solved.
- Analytics verified.
- End-to-end video production ready.
- Production verified.
