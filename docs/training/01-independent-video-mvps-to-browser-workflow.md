# From Independent Video MVPs to a Browser Workflow

## The important distinction

An MVP proves one reusable capability. A vertical slice composes already proven capabilities into one observable creator result. A dashboard screenshot proves presentation; it does not prove source, transcript, translation, voice or publication ownership.

## Example: URL to source manifest

```text
Browser command
  -> Workflow Run admits canonical input
  -> Graph Process starts Source Intake
  -> Source Intake calls Platform I/O public launcher
  -> Platform I/O downloads and probes media
  -> Source Intake commits manifest + receipt
  -> Graph verifies committed paths and fingerprint
  -> Dashboard projects COMPLETED
```

If Platform I/O fails, Source Intake writes a failed receipt and no success manifest. Graph stops the dependent verify node. The browser reports the copied failure; it does not invent recovery or success.

## Why loops are independent

Media, transcript chunks, translation segments, voice clips and publication targets have different retry costs and owners. Each Loop Engineering capability therefore has its own ordered identities, checkpoint file, adapter and terminal receipt. Graph Engineering composes these receipts without taking their write authority.

## Adding a new adapter

1. Preserve the public input/output contract.
2. Add deterministic fake-adapter domain evidence.
3. Verify a real output in the target runtime.
4. Record the exact platform/model evidence and gaps.
5. Connect it through the public adapter port; never import another MVP's private module.

## Reading evidence correctly

`DOMAIN_VERIFIED` means the contracts and adjacent behavior work. `PLATFORM_INTEGRATED` applies only when the named real runtime/platform has fresh evidence. `PRODUCTION_VERIFIED` additionally requires recovery, security, scale and representative operations.
