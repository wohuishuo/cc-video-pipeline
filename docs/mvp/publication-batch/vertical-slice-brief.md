# Publication Batch vertical-slice brief

| Field | Contract |
| --- | --- |
| Observable result | One Localization Manifest becomes an ordered, complete set of private/draft Publication Plans covering every localized derivative and selected platform, with one derivative active at a time. |
| Use cases | `plan` commands the batch; `doctor` reports portability and serial policy; the receipt reports resumable continuation; the aggregate plan reports committed derivative/metadata/child-plan facts. |
| State owners | Localization owns derivatives; Publication owns each one-video plan; Publication Batch alone owns rendered metadata and cross-derivative continuation; Studio owns only its run projection. |
| Protected invariants | immutable input fingerprint, exact derivative and target order, stable child IDs, maximum concurrency one, hash-fenced reuse, conflict before mutation, and no aggregate success after partial failure. |
| Decision gates | automatic execution, public visibility, platform-specific metadata rules, scheduling, thumbnails and retention remain unapproved. |
| Non-goals | platform contact, upload, secret custody, metadata-quality certification, hosted/mobile shells, production load and power-loss verification. |
