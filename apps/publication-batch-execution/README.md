# Publication Batch Execution

Execute every child plan in one confirmed Publication Batch Plan, strictly one at a time:

```powershell
.\apps\publication-batch-execution\run.ps1 execute C:\Jobs\publication-batch-plan.json `
  --confirmation 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef `
  --credential-vault "$env:LOCALAPPDATA\VideoGraphStudio\credential-vault.json" `
  --output-dir C:\Jobs\publication-batch-execution `
  --operation-id release-execution-001 `
  --json
```

The entire batch is preflighted before the first child starts. Current execution policy accepts credential-backed private YouTube plans only. Bilibili, Douyin, TikTok, public publication and uncredentialed jobs are rejected without contacting a platform.

This program owns only batch continuation and its aggregate manifest. Publication owns each child execution, YouTube Publisher owns each upload attempt and Credential Vault owns secret custody. Completed children are reused by verified hashes; ordinary failures resume independently; an uncertain upload is durably `UNKNOWN` and never retried automatically.
