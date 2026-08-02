# Engineering Review Checklist

## Boundary

- [ ] One authoritative writer is named for every new mutable artifact.
- [ ] Graph code owns coordination only; loop/domain truth remains in its MVP.
- [ ] Integration uses a public CLI, HTTP or versioned file contract.
- [ ] Desktop, hosted and mobile transports can be replaced without migrating domain ownership.

## Lifecycle

- [ ] Operation and correlation identities are stable and observable.
- [ ] Same-input replay is idempotent; changed-input reuse conflicts.
- [ ] Partial output is not publicly committed before validation.
- [ ] Restart resumes the first missing checkpoint and preserves completed work.
- [ ] Cancellation and unknown external outcomes have explicit states.

## Security and operations

- [ ] Paths are canonicalized and constrained to allowed roots.
- [ ] Child commands use argv arrays rather than interpolated shell text.
- [ ] Secrets are absent from logs, receipts and source control.
- [ ] Secret intake avoids argv, public results are redacted and workflows retain only credential references.
- [ ] Resource, timeout and platform-rate bounds are explicit.
- [ ] Run state, ordered logs and artifact fingerprints support diagnosis.

## Evidence

- [ ] Tests prove domain rules and relevant failure paths.
- [ ] Real-runtime claims cite a fresh run or receipt.
- [ ] Delivery ledger lists evidence missing and forbidden claims.
- [ ] `PRODUCTION_VERIFIED` is withheld without recovery, security, load and representative operations evidence.
