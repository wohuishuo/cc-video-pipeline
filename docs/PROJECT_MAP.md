# Repository MVP Map

```mermaid
flowchart TB
    ROOT[Repository]
    ROOT --> APPS[apps/ — public MVPs]
    ROOT --> PACKAGES[packages/ — shared contracts]
    ROOT --> PROJECTS[projects/ — concrete productions]
    ROOT --> DOCS[docs/ — guides and evidence]
    ROOT --> COMPAT[tools/ and .claude/skills/ — compatibility implementations]
    ROOT -. ignored .-> RUNTIME[models, caches, downloads, renders, profiles]

    classDef public fill:#f5f3ff,stroke:#7c3aed,color:#2e1065;
    classDef data fill:#ecfdf5,stroke:#16a34a,color:#052e16;
    classDef support fill:#eff6ff,stroke:#2563eb,color:#172554;
    classDef ignored fill:#f8fafc,stroke:#64748b,color:#334155,stroke-dasharray: 5 5;
    class APPS public;
    class PROJECTS data;
    class PACKAGES,DOCS,COMPAT support;
    class RUNTIME ignored;
```

## Reusable programs

`apps/` contains public applications. Each application owns one result and has an independent launcher, installer, manifest, README, tests, and evidence.

`apps/creator-batch/` is the reusable cross-item continuation owner. It consumes Creator Discovery facts and public child-MVP facts; it does not own or import media-processing internals.

`apps/publication-batch/` is the reusable cross-derivative planning owner. It consumes Localization facts and invokes Publication through its public launcher; it does not own localized media, upload state or credentials.

`apps/publication-batch-execution/` is the reusable cross-plan execution owner. It consumes an exact confirmed Publication Batch fact and invokes Publication and Credential Vault only through their public launchers; it owns continuation and aggregate verification, never child upload state or secret material.

## Shared contracts

`packages/` may contain versioned schemas and small process primitives. Shared packages never coordinate an application workflow or own project state.

## Concrete productions

`projects/` contains scripts, timing manifests, footage references, and assets for individual videos. Project content may be Chinese, English, Russian, or another source language. It is not reusable application code.

## Compatibility code

`tools/`, `.claude/skills/`, `research_mvp/`, and `video_platform/` currently host proven implementations behind the new application launchers. They can be migrated internally without changing the public MVP commands.

## Evidence

`docs/mvp/<name>/` records the observable result, capability DAG, executable evidence, and honest delivery level. `DESIGNED` and `IMPLEMENTED` do not mean production verified.
