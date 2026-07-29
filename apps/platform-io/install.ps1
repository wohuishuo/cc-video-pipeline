$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
& (Join-Path $root "tools\install_video_downloaders.ps1")
& (Join-Path $root "tools\install_video_uploaders.ps1")
