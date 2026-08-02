# Video Graph Studio capability DAG

```mermaid
flowchart LR
    URL["Creator account URL"] --> D["Creator Discovery"]
    D --> C["Verified Creator Catalog"]
    C --> S["Creator Selection"]
    S --> B["Creator Batch continuation"]
    LP["Languages + provider + voices"] --> B
    B --> I["Source Intake per video"]
    I --> A["Transcription"]
    A --> T["NLLB or DeepSeek Translation"]
    T --> V["Voice Rendering"]
    V --> L["Localization"]
    L --> O["Verified localized derivatives"]
    R["Per-language destination routes"] --> P["Publication intent"]
    O --> P
    P --> Y["YouTube private-ready"]
    P --> Q["Bilibili / Douyin / TikTok plan-only"]
```

Studio owns admission, continuation and browser projection only. Discovery owns the account catalog, Selection owns the exact subset, Creator Batch owns serial cross-item continuation, and media capabilities own their manifests. Destination intent does not claim publication execution. See the [full DAG](../../project/evidence/video-graph-studio/capability-dag.md).
