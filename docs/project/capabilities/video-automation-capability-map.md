# Video Automation Capability Map

An independent capability may consume another capability's published contract. It never reads or mutates the other capability's private state.

```mermaid
flowchart LR
    G1["G01 Graph Definition"] --> G3["G03 Workflow Process"]
    G2["G02 Workflow Run Owner"] --> G3
    S1["S01 Source Classification"] --> S2["S02 Folder Discovery"]
    S1 --> S3["S03 Platform Download Adapter"]
    S2 --> S4["S04 Source Manifest Owner"]
    S3 --> S4
    S4 --> T1["T01 Transcript Job Owner"]
    T1 --> T2["T02 ASR Adapter"]
    T2 --> T3["T03 Transcript Artifact"]
    T3 --> L1["L01 Translation Job Owner"]
    L1 --> L2["L02 Translation Adapter"]
    L2 --> L3["L03 Translation Artifact"]
    L3 --> V1["V01 Voice Segment Loop"]
    L3 --> C1["C01 Subtitle Renderer"]
    V1 --> C2["C02 Audio Mix"]
    C1 --> C3["C03 Video Composition"]
    C2 --> C3
    C3 --> P1["P01 Publication Plan"]
    P1 --> P2["P02 Platform Upload Adapter"]
    G3 -. "commands only" .-> S4
    G3 -. "commands only" .-> T1
    G3 -. "commands only" .-> L1
    G3 -. "commands only" .-> V1
    G3 -. "commands only" .-> C3
    G3 -. "commands only" .-> P1
```

## Build order and evidence gate

| ID | Capability | Current evidence | Next gate |
| --- | --- | --- | --- |
| G01-G03 | Graph definition, run and process ownership | `DOMAIN_VERIFIED` | crash/restart drill and production operations |
| S01-S04 | Source Intake | `DOMAIN_VERIFIED`; live YouTube evidence | profile enumeration and three remaining platforms |
| T01-T03 | Transcription | legacy `IMPLEMENTED` only | versioned manifest contract and real one-file receipt |
| L01-L03 | Translation | `DESIGNED` | adapter-neutral contract, human-editable artifact and quality checks |
| V01 | Voice segment loop | Edge implementation exists | adapter-neutral receipt and stable real completion |
| C01-C03 | Subtitle, audio and composition | partial implementation | independently verified media derivative |
| P01-P02 | Publication | guarded preparation exists | authenticated private/draft evidence per platform |

## Required substitutes

Tests may use fake ASR, translation, TTS and platform adapters only when they preserve operation identity, output shape, failure semantics and ownership. A fake adapter proves composition, not external quality or availability.
