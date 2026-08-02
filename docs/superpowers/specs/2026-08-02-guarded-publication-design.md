# Guarded Publication design

## Goal

Prepare and execute fingerprinted, idempotent publication jobs without allowing an ordinary browser click to publish unexpectedly.

## Two-phase contract

1. `plan` verifies a local MP4, metadata JSON, target/account mappings and visibility policy. It writes an immutable Publication Plan.
2. `execute` requires the exact plan SHA-256 as a confirmation token, re-verifies every input, then calls Platform I/O one job at a time and checkpoints each result.

Default visibility is private/draft. Execution is rejected when a platform adapter cannot guarantee private/draft. Public execution requires the plan to have been created with explicit public policy and still requires the plan hash at execution time.

## Ownership

Publication owns intent, confirmation, serial continuation and per-target receipts. Platform I/O owns login profiles and platform commands. Localization owns the MP4. Metadata remains an editable external artifact. Graph Studio may create a plan and observe receipts but never owns platform sessions.

## Recovery

Completed targets are reused only when plan and job fingerprints still match. Failed targets resume without repeating completed publications. Changed inputs conflict under the same operation. A failed run never claims global completion.

## Honest limits

No platform becomes platform-integrated until an account owner completes a private/draft upload and the result is verified on that platform. Bilibili, Douyin and TikTok currently lack a proven private/draft visibility guarantee in the pinned uploader.
