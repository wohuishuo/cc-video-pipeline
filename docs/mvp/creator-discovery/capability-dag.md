# Creator Discovery capability DAG

```mermaid
flowchart LR
    U["Creator URL"] --> C["Classify platform"]
    C --> A["Select profile adapter"]
    A --> P["Enumerate one page"]
    P --> D["Canonicalize and deduplicate"]
    D --> R["Atomic cursor checkpoint"]
    R -->|has more| P
    R --> M["Creator Manifest"]
```

URL classification and the manifest owner are adapter-neutral. yt-dlp and pinned F2 are replaceable platform adapters. Graph Studio may consume the final manifest but cannot own the cursor or item set.
