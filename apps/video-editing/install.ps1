if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { throw "ffmpeg is required and was not found on PATH." }
Write-Output "Video Editing is ready. Reframe additionally requires Python, MediaPipe, and OpenCV."
