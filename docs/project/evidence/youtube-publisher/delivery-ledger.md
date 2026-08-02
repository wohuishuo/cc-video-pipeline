# YouTube Publisher delivery ledger

| Field | Record |
| --- | --- |
| Supported completion level | `DOMAIN_VERIFIED` |
| Evidence present | independent launcher and manifest; redacted OAuth contract; private-only resumable upload; range resume; bounded retry; external-ID requirement; idempotent completed receipt; unknown-outcome fence; Platform I/O public-boundary composition |
| Evidence missing | authenticated channel upload, consent bootstrap, external-ID reconciliation query, quota/rate-limit and revocation operations |
| Substitutes | fake HTTP transport and fake child execution response |
| Decisions unapproved | public posting, hosted secret custody, paid quota and channel policy |
| Forbidden claims | deterministic protocol tests are not a real YouTube upload |
