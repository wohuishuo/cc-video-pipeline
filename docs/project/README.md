# Video Production Project System

Build creator results from product rules to executable evidence. Each lower layer must obey the ownership and completion rules defined above it.

## Reading order

1. Product specs describe an observable creator result and explicit non-goals.
2. Capability documents divide that result into independent, reusable owners.
3. Architecture defines contracts, state ownership and allowed dependency direction.
4. Engineering defines lifecycle, retry, security and verification rules.
5. Evidence records what a real command or test proved and what remains unproven.

```text
Creator result
  -> product rule
    -> capability MVP
      -> owner and contract architecture
        -> engineering rule
          -> work, tests and receipts
```

The structure follows the proven documentation chain in `roblox-city-scavenger`, adapted to local and future hosted video automation.

## Operating set

- [Creator Automation Studio product definition](product/creator-automation-studio.md)
- [Video automation capability map](capabilities/video-automation-capability-map.md)
- [Workspace Access MVP](../../apps/workspace-access/README.md)
- [Workspace Storage MVP](../../apps/workspace-storage/README.md)
- [Credential Vault MVP](../../apps/credential-vault/README.md)
- [Client Contracts MVP](../../apps/client-contracts/README.md)
- [System component map](architecture/system-component-map.md)
- [Component catalog](architecture/component-catalog.md)
- [Video Graph Studio blueprint](architecture/design/blueprints/video-graph-studio.md)
- [Public contract catalog](architecture/design/contracts/README.md)
- [Graph and Loop Engineering operating model](engineering/graph-loop-operating-model.md)
- [Engineering review checklist](engineering/rules/review-checklist.md)
- [Capability roadmap](planning/capability-roadmap.md)
- [Delivery evidence index](evidence/README.md)
- [Dependency review](reviews/graph-loop-dependency-review.md)
- [Training: independent MVPs to browser workflow](../training/01-independent-video-mvps-to-browser-workflow.md)
- [Training: lifecycle and operations verification](../training/02-lifecycle-and-operations-verification.md)
- [Training: secure local workspace admission](../training/03-secure-workspace-admission.md)
- [Training: route multiple local workspaces](../training/04-multi-workspace-studio.md)
