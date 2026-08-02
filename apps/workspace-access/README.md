# Workspace Access MVP

Workspace Access independently owns workspace identity, canonical filesystem roots and least-privilege bearer credentials. It is the admission-policy foundation for a future hosted or mobile client; it does not own Graph runs, media, platform accounts or billing.

Delivery level: `DOMAIN_VERIFIED`. Token lifecycle, scope, expiry, revocation, atomic persistence and redaction are verified locally. No hosted identity provider, remote secret vault or production security claim is made.

## Initialize a workspace

```powershell
.\apps\workspace-access\run.ps1 init `
  --registry "$env:LOCALAPPDATA\VideoGraphStudio\workspace-access.json" `
  --workspace-id local `
  --display-name "Local Studio" `
  --allowed-root "$HOME\Videos" `
  --json
```

Repeating the same identity replays safely. Reusing the ID with a different name or root set is a conflict.

## Issue a short-lived credential

```powershell
$issued = .\apps\workspace-access\run.ps1 issue `
  --registry "$env:LOCALAPPDATA\VideoGraphStudio\workspace-access.json" `
  --workspace-id local `
  --label desktop-browser `
  --scope runs:read `
  --scope runs:write `
  --ttl-hours 24 `
  --json | ConvertFrom-Json

$env:VIDEO_GRAPH_ACCESS_TOKEN = $issued.value.token
```

The plaintext credential is returned once. The registry stores only its SHA-256 digest, ID, label, scopes, timestamps and revocation state. Keep the plaintext token out of source control and command arguments.

## Authorize and revoke

```powershell
.\apps\workspace-access\run.ps1 authorize `
  --registry "$env:LOCALAPPDATA\VideoGraphStudio\workspace-access.json" `
  --workspace-id local `
  --required-scope runs:write `
  --token-env VIDEO_GRAPH_ACCESS_TOKEN `
  --json

.\apps\workspace-access\run.ps1 revoke `
  --registry "$env:LOCALAPPDATA\VideoGraphStudio\workspace-access.json" `
  --workspace-id local `
  --token-id TOKEN_ID_FROM_ISSUE `
  --json
```

Known scopes are `runs:read`, `runs:write`, `artifacts:read`, `publication:execute` and `admin`. `admin` satisfies any current scope and should be issued sparingly.

## Boundary

This MVP can be composed with an HTTP admission adapter later. The current Graph Studio remains loopback-only and does not yet require these credentials. File ACL hardening, tenant isolation, remote authentication, audit export and credential-vault integration remain separate capabilities.
