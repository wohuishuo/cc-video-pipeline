# Studio guarded-publication tutorial

Publishing is intentionally two Graphs. Choosing a target creates intent; it does not upload.

## 1. Store the credential

Use Credential Vault's environment-only input and provider metadata. Keep the returned credential ID; never paste the secret into Studio.

## 2. Run Publish Plan

Choose **Publish Plan**, one finished video, metadata JSON, account, YouTube target and credential ID. The completed run exposes `publication-plan.json` and its SHA-256. Planning contacts no platform.

## 3. Run Publish Execute

Choose **Publish Execute**. Studio automatically fills the newest completed credential-backed YouTube plan when available. Confirm:

- completed plan run ID;
- exact plan SHA-256;
- local Credential Vault registry path.

Execution is rejected unless the plan came from the same workspace, is unchanged, private/draft, YouTube-only and contains a valid credential reference. The run succeeds only when Publication commits a fingerprinted manifest with a non-empty external platform ID.

## 4. Evidence boundary

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/drills/studio-guarded-publication.ps1
```

The drill uses the real Studio, Publication and Credential Vault boundaries but a fake final platform child. It verifies orchestration and secret containment, not a real YouTube upload. Do not claim a social upload until the authenticated adapter and unknown-outcome reconciliation gates have their own evidence.
