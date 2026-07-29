# Contributing

## Add or change one MVP

An MVP must remain understandable and runnable without reading unrelated applications.

Required files:

```text
apps/<name>/
  README.md
  mvp.json
  install.ps1
  run.ps1
```

Its `mvp.json` must declare `schema_version`, `name`, `summary`, `entrypoint`, `install`, `test`, `inputs`, `outputs`, `dependencies`, and `delivery_level`.

## Development loop

1. Define one observable result and its unique state owner.
2. Write a failing contract test.
3. Implement the smallest runnable dependency closure.
4. Verify the focused test and one adjacent integration.
5. Record the capability DAG, failure evidence, substitutes, and honest delivery level.
6. Run repository validation.

```powershell
.\.venv\Scripts\python.exe -m scripts.validate_mvp_manifests .
powershell -ExecutionPolicy Bypass -File .\scripts\test-all.ps1
git diff --check
```

## Documentation language

Reusable source documentation, CLI help, and application READMEs use English. User-authored scripts, subtitles, proper names, and project content retain their source language.

## Secrets

Never commit cookies, tokens, browser profiles, session data, or unredacted receipts. Upload verification stops at draft/private state unless public publication is explicitly authorized.

## Generated artifacts

Do not commit models, caches, downloaded media, synthesized audio, renders, frame dumps, PID files, or preview images. Put concrete project inputs under `projects/` and runtime outputs in ignored output directories.

## Evidence

Every MVP requires these files under `docs/mvp/<name>/`:

- `vertical-slice-brief.md`
- `capability-dag.md`
- `capability-evidence.md`
- `delivery-ledger.md`

Delivery levels are cumulative evidence claims. Choose the highest level actually demonstrated, not the level intended later.
