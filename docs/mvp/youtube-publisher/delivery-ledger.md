# YouTube Publisher delivery ledger

| Field | Record |
| --- | --- |
| Supported completion level | `DOMAIN_VERIFIED` |
| Evidence present | strict credential and metadata contracts; private-only policy; streamed resumable transfer; 308 continuation; bounded 5xx recovery; required external ID; atomic redacted receipt; duplicate and unknown fences; Platform I/O routing tests |
| Evidence missing | real OAuth consent/bootstrap; authenticated private upload; returned-ID lookup; quota/rate-limit exercise; token revocation/renewal operations; crash after server completion |
| Substitutes | deterministic fake HTTP transport and fake child process result |
| Decisions unapproved | automatic public/unlisted publication, paid quota, channel selection and hosted OAuth custody |
| Forbidden claims | no authenticated upload or platform integration has been proven |
