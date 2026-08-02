# YouTube Publisher MVP

This independent program uploads exactly one local video through the YouTube Data API resumable protocol and always requests `private` visibility. It does not own publication plans, Graph runs or encrypted secret storage.

The credential value is JSON held in an environment variable. It may contain `accessToken`, or the refreshable set `clientId`, `clientSecret`, `refreshToken`. Credential Vault should inject that value into this one child process.

```powershell
$env:VIDEO_PLATFORM_CREDENTIAL = '{"clientId":"...","clientSecret":"...","refreshToken":"..."}'
.\apps\youtube-publisher\run.ps1 upload C:\Media\video.mp4 `
  --metadata C:\Media\metadata.json `
  --credential-env VIDEO_PLATFORM_CREDENTIAL `
  --output-dir C:\Media\youtube-output `
  --operation-id upload-001 --json
Remove-Item Env:\VIDEO_PLATFORM_CREDENTIAL
```

The receipt never contains OAuth material or the resumable-session URL. A matching completed operation replays without network access. An unknown outcome is fenced from automatic replay because a blind retry could create a duplicate video.

Current evidence uses deterministic fake HTTP transports. Do not describe this capability as platform-integrated until a channel owner deliberately performs and verifies a private upload.
