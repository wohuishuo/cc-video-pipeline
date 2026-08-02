# Secure Local Workspace Admission

This tutorial composes Workspace Access with Video Graph Studio without merging their state ownership. The result is an optional single-workspace security boundary for the local browser app.

## 1. Initialize the policy owner

Choose the filesystem root that this Studio instance may browse. Workspace Access canonicalizes it and owns the registry; Studio never edits the registry.

```powershell
$registry = "$env:LOCALAPPDATA\VideoGraphStudio\workspace-access.json"

.\apps\workspace-access\run.ps1 init `
  --registry $registry `
  --workspace-id local `
  --display-name "Local Studio" `
  --allowed-root "$HOME\Videos" `
  --json
```

## 2. Issue the least privilege needed

The browser needs run reads, run mutations and artifact browsing for the complete Studio UI.

```powershell
$issued = .\apps\workspace-access\run.ps1 issue `
  --registry $registry `
  --workspace-id local `
  --label desktop-browser `
  --scope runs:read `
  --scope runs:write `
  --scope artifacts:read `
  --ttl-hours 24 `
  --json | ConvertFrom-Json

$issued.value.token
```

The plaintext appears once. The registry stores only a digest and lifecycle metadata. Do not place the token in a script, Git, argv or a durable URL.

## 3. Bind one Studio process

```powershell
.\apps\video-graph-studio\run.ps1 `
  -AccessRegistry $registry `
  -WorkspaceId local
```

Open **Access** in the top bar, enter `local` and paste the credential. The credential stays in that browser tab's session storage. Closing the browser session clears it.

## 4. Understand the contract

```mermaid
sequenceDiagram
    participant Browser
    participant Admission as Studio Admission
    participant Access as Workspace Access CLI
    participant Run as Run Application
    Browser->>Admission: Bearer + workspace + versioned request
    Admission->>Access: authorize(required scope), token via environment
    Access-->>Admission: redacted allow or deny
    alt allowed
        Admission->>Run: invoke query or command
        Run-->>Browser: projection or command result
    else denied
        Admission-->>Browser: 401 or 403; Run is not invoked
    end
```

`runs:read` protects run queries, `artifacts:read` protects folder browsing and `runs:write` protects mutations. Health and static assets remain public so a fresh browser can load the UI and discover that access is required.

## 5. Revoke without changing Studio

Use the credential ID returned by `issue`:

```powershell
.\apps\workspace-access\run.ps1 revoke `
  --registry $registry `
  --workspace-id local `
  --token-id TOKEN_ID `
  --json
```

The next protected request is denied. Studio owns no credential lifecycle and therefore needs no database edit or restart.

## Evidence boundary

This proves secure local composition, not hosted or production security. Read the [recorded admission drill](../project/evidence/video-graph-studio/secure-admission-drill.md) for exact probes. Multi-workspace routing is covered separately; remote identity, vault custody, hard quotas, attack review and operational security remain open.
