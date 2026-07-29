# Video platform I/O

Install on a new Windows computer:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\install_video_downloaders.ps1
powershell -ExecutionPolicy Bypass -File .\tools\install_video_uploaders.ps1
powershell -ExecutionPolicy Bypass -File .\video-platform.ps1 doctor
```

Download (anonymous first; cookie is optional):

```powershell
.\video-platform.ps1 download youtube "<url>" --output-dir downloads\youtube
.\video-platform.ps1 download bilibili "<url>" --output-dir downloads\bilibili
.\video-platform.ps1 download douyin "<url>" --output-dir downloads\douyin --cookies cookies.txt
.\video-platform.ps1 download tiktok "<url>" --output-dir downloads\tiktok --cookies cookies.txt
```

Prepare an upload without sending anything:

```powershell
.\video-platform.ps1 upload youtube video.mp4 --metadata metadata.json --account main
```

Login and deliberate execution:

```powershell
.\video-platform.ps1 login youtube --account main
.\video-platform.ps1 upload youtube video.mp4 --metadata metadata.json --account main --execute
```

Add `--public` only when a public YouTube upload is explicitly intended. Profiles and receipts are local ignored runtime data.
