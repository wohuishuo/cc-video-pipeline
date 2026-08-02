# Workflows

Applications are useful alone. These workflows show common compositions through files; none of them creates a new shared state owner.

## Discover a creator batch

```mermaid
flowchart LR
    PROFILE["Creator profile URL"] --> DISCOVER["Creator Discovery"]
    DISCOVER --> MANIFEST[("Creator Manifest")]
    MANIFEST --> INTAKE["Source Intake per selected URL"]
    INTAKE --> MEDIA[("Source Manifests")]
```

Discovery commits canonical URLs only. Downloading every item is a separate, explicitly selected composition so a large profile cannot silently consume storage or network bandwidth.

Select **Creator+Dub** when that explicit composition is intended:

```mermaid
flowchart LR
    MANIFEST["Creator Manifest"] --> LOOP["Creator Batch"]
    LOOP -->|"one item"| INTAKE["Source Intake"]
    INTAKE --> ASR["Transcription"]
    ASR --> TR["Translation"]
    TR --> VOICE["Voice Rendering"]
    VOICE --> LOC["Localization"]
    LOC -->|"committed fact"| LOOP
    LOOP --> BATCH[("Creator Batch Manifest")]
```

The loop continues after an item failure, but the aggregate manifest is withheld until every item has verified language and derivative coverage. Repeating the same operation reuses hash-verified items and retries only incomplete or stale items.

## Localize and plan a release batch

```mermaid
flowchart LR
    SOURCE["Folder or supported URL"] --> INTAKE["Source Intake"]
    INTAKE --> ASR["Transcription"]
    ASR --> TR["Translation"]
    TR --> VOICE["Voice Rendering"]
    VOICE --> LOC["Localization"]
    LOC --> MANIFEST[("Localization Manifest")]
    META[("Metadata template")] --> BATCH["Publication Batch"]
    TARGETS["Selected platforms and accounts"] --> BATCH
    MANIFEST --> BATCH
    BATCH -->|"one derivative at a time"| PLAN["Publication"]
    PLAN --> PLANS[("Private/draft child plans")]
    PLANS --> BATCH
    BATCH --> AGG[("Publication Batch Plan")]
```

Choose `Folder+Release` or `URL+Release` in Video Graph Studio. Publication Batch renders metadata tokens for each derivative and invokes Publication through its public launcher. It owns continuation and aggregate coverage only; it does not upload, publish, own media or hold credential values.

## Execute a confirmed release batch

```mermaid
flowchart LR
    RUN["Completed Release run"] --> PLAN[("Publication Batch Plan")]
    PLAN --> HASH{"Exact batch SHA confirmed?"}
    HASH -- no --> REJECT[("Reject before contact")]
    HASH -- yes --> PREFLIGHT{"Every target is credential-backed private YouTube?"}
    PREFLIGHT -- no --> REJECT
    PREFLIGHT -- yes --> LOOP["Publication Batch Execution"]
    VAULT["Credential Vault"] -. "one-child injection" .-> LOOP
    LOOP -->|"one plan at a time"| CHILD["Publication"]
    CHILD --> OUTCOME{"Completed / failed / unknown"}
    OUTCOME -- completed --> LOOP
    OUTCOME -- failed --> RETRY[("Durable retry checkpoint")]
    OUTCOME -- unknown --> FENCE[("Manual reconciliation fence")]
    LOOP -->|"all verified"| AGG[("Batch Execution Manifest")]
```

Choose `Release Execute` only after reviewing a completed Release plan. It is a separate two-node Graph with a separate exact-SHA confirmation. Publication Batch Execution owns serial continuation, reuses hash-verified completed children, retries known failures and refuses to retry an `UNKNOWN` platform outcome. Current policy rejects Bilibili, Douyin, TikTok, public jobs and uncredentialed jobs before platform contact.

## Research a reference video

```mermaid
flowchart LR
    URL[Video URL] --> IO[Platform I/O]
    IO --> VIDEO[(Verified media)]
    VIDEO --> TX[Transcription]
    VIDEO --> SIG[Signal Analysis]
    SIG --> CUTS[(Cut points)]
    VIDEO --> FRAMES[Frame Extraction]
    CUTS --> FRAMES
    TX --> DOSSIER[Channel Research]
    FRAMES --> DOSSIER
    DOSSIER --> REPORT[(Research dossier)]
```

## Edit and localize a recording

```mermaid
flowchart LR
    RAW[(Raw recording)] --> TX[Transcription]
    RAW --> EDIT[Video Editing]
    TX --> SCRIPT[(Corrected transcript)]
    REF[(Voice reference)] --> VOICE[Voice Cloning]
    SCRIPT --> LOC[Localization]
    VOICE --> LOC
    EDIT --> LOC
    LOC --> LOCALIZED[(Localized master)]
```

Localization is `PLATFORM_INTEGRATED`: its public manifest workflow and a real local FFmpeg/FFprobe browser run are verified. Production operations and social publication remain separate, unproven capabilities.

## Transcribe and translate from the browser

```mermaid
flowchart LR
    SOURCE["Folder or supported video URL"] --> INTAKE["Source Intake"]
    INTAKE --> TX["Transcription"]
    TX --> TM[("Transcript Manifest")]
    TM --> TR["Translation"]
    LANG["RU / EN / KK selection"] --> TR
    TR --> OUT[("Editable translation JSON + SRT")]
    CONTROL["Video Graph Studio"] -. "commands and verifies" .-> INTAKE
    CONTROL -. "commands and verifies" .-> TX
    CONTROL -. "commands and verifies" .-> TR
```

Choose `Folder+Translate` or `URL+Translate` in Video Graph Studio. The graph runs six durable steps with one worker. Translation output is marked `MACHINE`; it is not yet a dubbed or subtitle-burned video.

## Build visual cards and publish

```mermaid
flowchart LR
    SCRIPT[(Script / scene JSON)] --> STUDIO[Remotion Studio]
    ASSETS[(Project assets)] --> STUDIO
    STUDIO --> RENDER[(Rendered master)]
    RENDER --> PLAN[Publication Plan]
    META[(Metadata JSON)] --> PLAN
    PLAN --> HASH{Exact plan SHA confirmed?}
    HASH -- no --> PREPARED[(Verified plan only)]
    HASH -- yes --> POLICY{Visibility guaranteed?}
    POLICY -- no --> BLOCKED[(Policy rejection)]
    POLICY -- yes --> UPLOAD[Platform I/O]
    VAULT[Credential Vault] -. "one child environment" .-> UPLOAD
    UPLOAD --> YOUTUBE[YouTube Publisher]
    YOUTUBE --> PRIVATE[(Private receipt + video ID)]
```

## Download decision path

```mermaid
flowchart TD
    URL[Platform URL] --> ROUTE[Detect platform]
    ROUTE --> ANON[Anonymous yt-dlp attempt]
    ANON -->|success| PROBE[FFprobe verification]
    ANON -->|access blocked| COOKIE{Cookie supplied?}
    COOKIE -->|yes| RETRY[Authenticated retry]
    COOKIE -->|no| FALLBACK{Douyin or TikTok?}
    RETRY --> PROBE
    FALLBACK -->|yes| F2[f2 fallback]
    FALLBACK -->|no| FAIL[(Failure receipt)]
    F2 --> PROBE
    PROBE -->|valid media| OK[(Success receipt)]
    PROBE -->|missing or invalid| FAIL
```
