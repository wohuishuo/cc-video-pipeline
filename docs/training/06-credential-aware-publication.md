# Credential-aware publication tutorial

This flow keeps the publication plan useful for replay and review without turning it into a secret store.

## 1. Store the provider credential

```powershell
$vault = "$env:LOCALAPPDATA\VideoGraphStudio\credential-vault.json"
$env:YOUTUBE_CREDENTIAL = Get-Content -Raw "$HOME\Downloads\youtube-session.json"
& .\apps\credential-vault\run.ps1 put --vault $vault --credential-id youtube-main --provider youtube --label "Main" --secret-env YOUTUBE_CREDENTIAL --json
$env:YOUTUBE_CREDENTIAL = $null
```

## 2. Plan by reference

```powershell
& .\apps\publication\run.ps1 plan .\final.mp4 `
  --metadata .\metadata.json `
  --target youtube=main `
  --credential youtube=youtube-main `
  --output-dir .\publish-plan `
  --operation-id plan-001 --json
```

The generated job contains `credentialId: youtube-main`, never credential contents.

## 3. Confirm and execute

```powershell
$plan = Resolve-Path .\publish-plan\publication-plan.json
$sha = (Get-FileHash -Algorithm SHA256 $plan).Hash.ToLowerInvariant()
& .\apps\publication\run.ps1 execute $plan `
  --confirmation $sha `
  --credential-vault $vault `
  --output-dir .\publish-run `
  --operation-id publish-001 --json
```

Credential Vault rejects a provider mismatch before releasing plaintext. A successful local command still does not prove the platform accepted an upload; inspect the adapter's verified external ID and platform-specific evidence.

## 4. Reproduce the safe composition

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\drills\credential-aware-publication.ps1
```

The drill substitutes a deterministic child for the social platform, so it is safe and repeatable without publishing anything externally.
