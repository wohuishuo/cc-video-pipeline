# State Ownership Rules

1. Every mutable fact has one authoritative writer.
2. A graph owns dependency order and continuation, not the domain artifacts produced by its nodes.
3. A loop owns its stable item identities, checkpoint order and terminal receipt.
4. Projections and UI state are disposable readers and cannot authorize mutation.
5. Cross-owner communication uses a versioned command, query or committed fact.
6. A committed fact names an inspectable artifact and its upstream fingerprint.
7. Credentials terminate at the platform adapter that needs them.
8. Retry reuses the same operation identity; changed canonical input conflicts.
9. Unknown external outcomes are quarantined until reconciled.
10. A new client or storage adapter must not move domain truth into transport code.

These rules are the dependency test for future desktop, hosted and mobile work. If a change creates a second writer, imports private state across MVPs or lets presentation code declare success, it must be redesigned before merge.
