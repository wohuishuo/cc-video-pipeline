# Platform I/O MVP

Downloads media and prepares isolated uploads for YouTube, Bilibili, Douyin, and TikTok. Anonymous download is attempted first; cookies are optional. Uploads are prepared by default and execute only with `--execute`.

```powershell
.\install.ps1
.\run.ps1 doctor --json
.\run.ps1 download youtube "<url>" --output-dir downloads\youtube
```

See `docs/mvp/video-platform-io/` for verified platform limitations.
