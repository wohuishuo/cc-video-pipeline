# Tutorial: plan every localized video for target platforms

## Browser workflow

Start Video Graph Studio and select **Folder+Release** or **URL+Release**. Choose the source, languages, ASR and translation devices, then provide:

- a metadata-template JSON path;
- an account label;
- YouTube, Bilibili, Douyin and/or TikTok targets;
- an optional YouTube credential ID.

The twelve Graph steps run the existing ten-step localization workflow, then:

11. Publication Batch renders metadata and invokes Publication once per localized derivative.
12. Studio verifies exact derivative, metadata, child-plan and target coverage.

No platform is contacted. The result is a local `publication-batch-plan.json` plus one editable metadata file and one private/draft `publication-plan.json` per derivative.

## Metadata template

```json
{
  "title": "{filename} [{language}]",
  "description": "Localized version for {language}",
  "tags": ["{media_id}", "localized-{language}"]
}
```

Supported tokens are `{filename}`, `{language}` and `{media_id}`. Unknown or unbalanced brace tokens are rejected before any child plan runs. A literal title without tokens is allowed when intentionally sharing the same title.

## Standalone workflow

```powershell
.\apps\publication-batch\run.ps1 plan C:\Jobs\localization-manifest.json `
  --metadata-template C:\Jobs\metadata.json `
  --target youtube=primary --credential youtube=youtube-main `
  --target tiktok=brand `
  --output-dir C:\Jobs\publication-batch `
  --operation-id release-plan-001 --json
```

## Resume and inspection

If one child plan fails, later derivatives are still attempted and the aggregate remains absent. Repeat the same command after correcting the local input: verified child plans are skipped, incomplete or stale children reuse their original identities, and changed batch input under the same operation ID is rejected.

Inspect `publication-batch-receipt.json` for progress and `publication-batch-plan.json` for complete coverage. Upload remains a separately confirmed workflow; this command cannot publish or make a video public.
