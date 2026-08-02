# YouTube Publisher vertical-slice brief

## Outcome

Given one video, metadata and an OAuth credential injected by name, create one private YouTube resumable upload and commit a redacted receipt with its external video ID.

## Boundary

The application owns OAuth refresh, YouTube HTTP protocol, private-only policy and its receipt. Credential Vault owns encrypted custody; Platform I/O owns platform routing; Publication owns confirmed multi-job execution.

## Definition of done

Domain verification requires deterministic OAuth, session, resume, redaction, idempotency and unknown-outcome tests. Platform integration additionally requires a channel owner to verify one deliberate private upload and its returned ID.
