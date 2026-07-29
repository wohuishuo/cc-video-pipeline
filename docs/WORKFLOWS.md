# Workflows

Applications are useful alone. These workflows show common compositions through files; none of them creates a new shared state owner.

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

Localization is currently `DESIGNED`; the diagram documents the intended public file contracts, not a production-verification claim.

## Build visual cards and publish

```mermaid
flowchart LR
    SCRIPT[(Script / scene JSON)] --> STUDIO[Remotion Studio]
    ASSETS[(Project assets)] --> STUDIO
    STUDIO --> RENDER[(Rendered master)]
    RENDER --> UPLOAD[Platform I/O]
    META[(Metadata JSON)] --> UPLOAD
    UPLOAD --> GUARD{--execute?}
    GUARD -- no --> PREPARED[(Prepared command)]
    GUARD -- yes --> PRIVATE[(Draft / private upload)]
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
