if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { throw "ffmpeg is required and was not found on PATH." }
Write-Output "Frame Extraction is ready."
