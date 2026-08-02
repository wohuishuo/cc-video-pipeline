# Platform I/O MVP

Downloads media and prepares isolated uploads for YouTube, Bilibili, Douyin, and TikTok. Anonymous download is attempted first; cookies are optional. Uploads are prepared by default and execute only with `--execute`.

```powershell
.\install.ps1
.\run.ps1 doctor --json
.\run.ps1 download youtube "<url>" --output-dir downloads\youtube
```

See `docs/mvp/video-platform-io/` for verified platform limitations.

Authenticated callers can name an environment boundary without putting its value in argv:

```powershell
.\run.ps1 upload youtube final.mp4 --metadata metadata.json --account primary `
  --credential-env VIDEO_PLATFORM_CREDENTIAL --execute --json
```

The command rejects a missing or empty named environment variable, never echoes its value and lets the selected upstream child inherit it. Credential Vault and Guarded Publication compose this contract automatically. Whether an upstream uploader understands the credential or session format remains that platform adapter's responsibility.
