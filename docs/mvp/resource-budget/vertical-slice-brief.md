# Resource Budget vertical slice brief

| Field | Record |
| --- | --- |
| Observable result | competing local processes cannot reserve more workspace bytes or execution slots than configured |
| Use cases | configure, reserve, renew, release, describe and snapshot |
| State owner | Resource Budget alone writes budget configuration and leases |
| Protected invariants | transactional no-oversubscription, stable reservation identity, generation fencing, TTL lifecycle and idempotent terminal release |
| Decision gates | hosted store, budget tiers, GPU/network units, preemption and billing |
| Non-goals | filesystem truth, workflow completion, authentication, distributed consensus and production tenancy |
