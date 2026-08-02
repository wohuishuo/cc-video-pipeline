# Publication Batch Execution vertical-slice brief

| Field | Contract |
| --- | --- |
| Observable result | One exact, confirmed Publication Batch Plan becomes an ordered set of verified private YouTube publication facts, with no more than one child active at a time. |
| Use cases | `execute` preflights the whole batch, resumes ordinary failures, fences uncertain uploads and publishes an aggregate manifest only after every child is verified; `doctor` reports the supported policy and dependencies. |
| State owners | Publication Batch owns the ordered plans; Publication owns each child execution receipt; YouTube Publisher owns each upload attempt; Credential Vault owns secret custody; Publication Batch Execution alone owns cross-plan continuation and its aggregate manifest; Studio owns only its run projection. |
| Protected invariants | exact batch-plan SHA confirmation, immutable operation fingerprint, credential-backed private YouTube only, stable item and child operation IDs, maximum concurrency one, hash-verified reuse, no automatic retry after uncertainty, and no aggregate success after partial failure. |
| Decision gates | real account execution, additional platform adapters, public visibility, scheduling, rate-limit policy, reconciliation UI, hosted secrets and commercial tenancy remain unapproved. |
| Non-goals | translation, media generation, plan creation, credential storage, direct platform adapter ownership, automatic public posting, distributed execution and production-scale verification. |

