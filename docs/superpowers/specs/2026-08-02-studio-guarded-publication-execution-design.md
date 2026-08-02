# Studio guarded publication execution design

## Promise

A creator may turn one already completed Studio publication-plan run into a separate execution Graph, but only after supplying the exact plan SHA-256 and a local Credential Vault path. The browser path is restricted to private YouTube because that is the only current adapter with an evidenced visibility guarantee.

## State owners

- Publication owns immutable plan, per-target checkpoints, execution receipt and publication manifest.
- Credential Vault owns encrypted credential custody and provider-bound child injection.
- Platform I/O owns the platform adapter process and external receipt.
- Studio Run owns only Graph lifecycle and committed adapter references.
- The browser owns only disposable selection/input state.

## Admission and lifecycle

1. Publication Plan accepts optional non-secret credential IDs and commits them into target jobs.
2. Execute creation names a completed plan `runId`, not an arbitrary plan path.
3. Studio resolves the verified plan artifact from that same workspace's RunStore and requires the supplied confirmation to equal its committed SHA-256.
4. The plan must be private/draft, YouTube-only and credential-referenced. Credential Vault must be an existing file below the current user home.
5. The execution node invokes Publication's public `execute` command, which in turn composes Credential Vault and Platform I/O.
6. A verifier accepts only a fingerprint-matching Publication manifest whose jobs are completed and have non-empty external IDs.

## Failure and safety

- Planning never uploads.
- Execution is a distinct explicit Graph; selecting targets is not confirmation.
- Changed plan bytes, wrong SHA, missing credential reference, public plans and platforms without private guarantees fail before Platform I/O.
- Credential contents never enter Studio parameters, argv, logs or receipts.
- A child process without a trustworthy external ID cannot commit success.
- Unknown remote outcome reconciliation remains a platform promotion gate; this slice is domain-tested with a fake uploader and does not claim real authenticated upload.

## Verification boundary

Tests prove same-workspace plan provenance, exact confirmation, private YouTube policy, credential-reference propagation, public launcher composition, manifest verification and no-secret state. Real external platform execution is intentionally not performed.
