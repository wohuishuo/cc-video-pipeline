# Source Intake vertical slice brief

Observable result: turn one local media folder or one supported social-video URL into a deterministic, versioned `source-manifest.json` plus an `intake-receipt.json` that another MVP can consume without importing Source Intake internals.

Source Intake owns discovery, the manifest, its receipt, idempotency and redaction. Platform I/O owns network download mechanics. Video Graph Studio owns workflow continuation. Translation, speech synthesis, editing and publication are outside this slice.
