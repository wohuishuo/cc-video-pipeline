# Credential-aware Publication Drill

Date: 2026-08-02
Environment: Windows 11; real Guarded Publication and Credential Vault launchers; CurrentUser DPAPI; fake Platform I/O child

## Observable result

The public planner wrote a private YouTube job containing only credential reference `youtube-main`. Execution accepted the exact plan SHA-256, asked Credential Vault to verify provider `youtube`, recovered the real DPAPI ciphertext and injected it into one fake platform child as `VIDEO_PLATFORM_CREDENTIAL`.

| Probe | Result |
| --- | --- |
| Vault put | exit `0` |
| Publication plan | `COMPLETED`, exit `0` |
| Confirmed execution | `COMPLETED`, exit `0` |
| External ID | `credential-drill-123` |
| Credential reference used | `true` |
| Maximum active executions | `1` |
| Known plaintext in vault/plan/receipts/manifest/captured lifecycle output | `false` |
| Plan SHA-256 | `a09315bf0cce14f46eb17896549d68f3312c229ad092b3ae2cbfdfcb726ac277` |
| Manifest SHA-256 | `da178119d9659a012f0120be0eb23a6a347643f6a21088c4385fa1092e418575` |

Reproduce with `scripts/drills/credential-aware-publication.ps1`.

## Claim boundary

This proves public-command composition, provider isolation, redaction, exact confirmation and serial checkpointing. The child intentionally substitutes for a social platform. It does not prove that YouTube, Douyin, Bilibili or TikTok accepted a session or upload.
