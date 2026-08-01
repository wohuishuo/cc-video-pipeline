# ADR-001: Graph process manager coordinates independent loops

- **Status:** Accepted locally
- **Date:** 2026-08-02
- **Decision:** Use one durable Graph Process Manager to coordinate independently owned, serial Loop Engineering operations through public commands and committed receipts.

## Context

Video automation contains long external operations, partial completion, retries and replacement adapters. A single giant localization service would mix source, text, voice, media and platform authority.

## Decision

Each loop owns one repeatable artifact family and its checkpoints. The graph owns dependency order and continuation only. The browser renders copied run facts. Default execution is one active workflow and one child process; future concurrency requires a separate resource-budget owner and must not change artifact ownership.

## Consequences

- A completed transcript can survive translation or TTS failure.
- A new TTS or platform adapter can be selected without rewriting the graph store.
- Workflow recovery resumes from committed receipts rather than rerunning every node.
- More contracts and evidence records are required, but failures remain attributable.
