# Graph and Loop Video Automation System Design

## Goal

Evolve the local Video Graph Studio into a reusable creator automation product where Graph Engineering coordinates multiple independently owned Loop Engineering capabilities for intake, transcription, translation, voice, composition and publication.

## Architectural choice

Adopt the ownership, committed-fact, process-manager, projection and evidence-promotion model used by `wohuishuo/roblox-city-scavenger` at commit `a15e2731b93614c44bfd87ccb91408d953699a65`, translated to video automation rather than copied as Roblox-specific code.

## Boundaries

- Graph owns workflow continuation only.
- Each loop owns one artifact family and idempotent checkpoints.
- Browser and future mobile/hosted clients use versioned commands and projections.
- Adapters terminate external platform/model concerns.
- Evidence ledgers prevent domain tests from becoming production claims.

## Delivery sequence

Complete source intake first, then create transcript artifacts from a source manifest, then translation, voice/subtitle assets, composition, creator-profile enumeration and guarded publication. Parallel execution is postponed until a resource-budget owner exists.

## Acceptance

The project contains a product definition, capability DAG, system map, component catalog, ADR, operating model, evidence index, roadmap, dependency review and training guide. Tests enforce the presence of these layers and their central ownership/idempotency vocabulary.
