# State Ownership Rules

1. Every mutable fact has one authoritative writer.
2. A graph owns dependency order and continuation, not the domain artifacts produced by its nodes.
3. A loop owns its stable item identities, checkpoint order and terminal receipt.
4. A start queue owns only requested run order and claim lifecycle; it cannot change domain checkpoints.
5. Projections and UI state are disposable readers and cannot authorize mutation.
6. Cross-owner communication uses a versioned command, query or committed fact.
7. A committed fact names an inspectable artifact and its upstream fingerprint.
8. Credential Vault owns encrypted local custody; decrypted values terminate only in the selected child platform adapter.
9. Retry reuses the same operation identity; changed canonical input conflicts.
10. Unknown external outcomes are quarantined until reconciled.
11. A new client or storage adapter must not move domain truth into transport code.

These rules are the dependency test for future desktop, hosted and mobile work. If a change creates a second writer, imports private state across MVPs or lets presentation code declare success, it must be redesigned before merge.
