# Documentation Experience Design

## Goal

Turn the repository documentation into a visual, trustworthy product guide that lets a first-time visitor understand the system in 30 seconds and run one independent MVP in five minutes.

## Information architecture

The root README is the landing page: value proposition, badges, capability map, end-to-end workflow, quick start, application catalog, evidence legend, and documentation links. Detailed explanations move to `docs/ARCHITECTURE.md`, `docs/WORKFLOWS.md`, and `docs/CONTRIBUTING.md`. Application READMEs remain the source of truth for application-specific commands.

## Visual system

Use GitHub-native Markdown and Mermaid only. Diagrams use consistent meanings: blue for input and orchestration, purple for independent MVPs, green for verified artifacts, orange for external platforms, and gray for project-owned data. No external diagram service, generated binary, or screenshot is required.

## Diagrams

1. A creator workflow from source discovery through publishing.
2. An independence map showing applications communicating through files and public CLIs.
3. A platform I/O flow showing anonymous-first download, optional cookies, verification, receipts, and guarded upload execution.
4. A repository ownership map separating reusable applications, shared contracts, concrete projects, and generated artifacts.

## Accuracy rules

Delivery labels come from `apps/*/mvp.json`. `DESIGNED`, `IMPLEMENTED`, and `DOMAIN_VERIFIED` are explained explicitly. Documentation must not claim all platforms, models, or uploads are production verified. Commands must use paths that exist in the repository.

## Verification

Repository tests check that the README links all applications and documentation pages, contains Mermaid workflows, contains no mojibake, and preserves evidence language. The manifest validator and full Python suite remain required before publishing.

## Non-goals

- A hosted documentation website.
- External badge or diagram dependencies beyond stable GitHub shields.
- Translating user-authored scripts, subtitles, or project content.
- Hiding known platform or model limitations.
