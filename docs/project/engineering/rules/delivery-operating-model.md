# Delivery Operating Model

Work proceeds from the lowest unproven dependency, one independently verifiable capability at a time.

```text
product promise
  -> capability owner and invariant
    -> public contract
      -> deterministic domain evidence
        -> real adapter/platform evidence
          -> recovery, security and operations evidence
```

## Required loop

1. Define the observable result and explicit non-goals.
2. Name the state owner and forbidden responsibilities.
3. Specify replay, conflict, cancellation and failure semantics.
4. Implement the smallest runnable MVP with a public launcher.
5. Verify it independently with deterministic evidence.
6. Compose it only through its public contract.
7. Record exact proof, missing proof and forbidden claims.
8. Promote the delivery level only when fresh evidence supports it.

Parallel execution is a later capacity policy, not a default architecture. It requires explicit CPU, GPU, memory, network and platform-rate budgets plus deterministic join and cancellation semantics.

Commercialization work begins at the edges: authenticated admission, tenant identity, secret custody, quotas, billing and remote artifact storage become explicit owners. The media-domain MVPs remain independently runnable.
