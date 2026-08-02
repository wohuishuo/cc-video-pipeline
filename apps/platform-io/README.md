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

The command rejects a missing or empty named environment variable and never echoes its value. A credential-backed private YouTube execution routes through the repository-owned [YouTube Publisher](../youtube-publisher/README.md), which consumes OAuth JSON, uses the resumable Data API protocol and requires a non-empty external video ID. Other upload targets remain isolated third-party browser adapters and do not yet consume this OAuth contract.
