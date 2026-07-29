# Capability DAG

```text
portable installer
  -> dependency doctor
  -> platform URL router
  -> anonymous yt-dlp download
      -> optional cookie retry
      -> Douyin/TikTok f2 fallback
      -> FFprobe media verification
      -> atomic receipt

isolated account profile
  -> platform login adapter
  -> prepared upload command
  -> explicit --execute
  -> draft/private platform verification
```

State owners stay separate: downloader owns downloaded media; FFprobe owns media facts; each upload adapter owns only its platform profile; the receipt layer owns evidence but no platform state.
