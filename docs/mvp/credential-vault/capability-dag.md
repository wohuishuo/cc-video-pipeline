# Credential Vault capability DAG

```mermaid
flowchart LR
    E["Secret environment variable"] --> P["CurrentUser DPAPI protect"]
    I["Credential ID + metadata"] --> P
    P --> R["Atomic encrypted registry"]
    R --> D["Redacted describe"]
    R --> U["Context-bound unprotect"]
    U --> C["One child environment"]
    R --> X["Rotate or revoke"]
```

Only Credential Vault writes the encrypted registry. A child receives plaintext for the duration of its process; the workflow and its receipts retain only the credential ID.
