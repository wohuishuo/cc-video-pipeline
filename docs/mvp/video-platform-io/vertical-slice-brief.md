# Portable video platform I/O — vertical slice brief

## Outcome

One portable command surface for four independent platform slices: YouTube, Bilibili, Douyin, and TikTok. Each slice owns URL validation, anonymous-first download, optional cookie retry, FFprobe verification, upload profile isolation, and a receipt.

## Boundary

- Download is allowed to execute immediately.
- Upload preparation is the default. `--execute` is required to touch a platform.
- YouTube upload defaults to private; no public post is used as a test.
- Platform login state remains inside `profiles/<platform>/<account>` and is never shared.

## Definition of done

A slice is production-verified only after a real downloaded file passes FFprobe or a real account upload reaches platform draft/private state. Installed adapters and passing unit tests alone do not count as production verification.
