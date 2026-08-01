# Source Intake capability DAG

```mermaid
flowchart LR
    folder[Local folder] --> discover[Deterministic media discovery]
    url[Supported HTTPS URL] --> classify[Platform classification]
    classify --> platform[Platform I/O public CLI]
    platform --> discover
    discover --> manifest[Versioned source manifest]
    manifest --> verify[Path and hash verification]
    verify --> receipt[Idempotent intake receipt]
```

Lowest independently proven capabilities are URL classification and folder discovery. URL mode substitutes the independently owned Platform I/O CLI for network behavior; it does not copy the downloader into this application.
