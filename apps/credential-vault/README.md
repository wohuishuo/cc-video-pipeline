# Credential Vault MVP

Credential Vault independently owns local provider-secret custody. On Windows it protects each secret with CurrentUser DPAPI, stores only encrypted ciphertext and redacted metadata, and can release one selected secret into one explicitly launched child-process environment. It does not know how YouTube, Douyin, TikTok or Bilibili authenticate and it does not own publication runs.

Delivery level: `DOMAIN_VERIFIED`. Lifecycle, redaction, contextual binding, atomic persistence, real DPAPI protection and real child-process injection are verified locally. This is not hosted key management or production tenant secret custody.

## Store a credential

Pass secret contents through an environment variable, never a command argument:

```powershell
$vault = "$env:LOCALAPPDATA\VideoGraphStudio\credential-vault.json"
$env:VIDEO_PLATFORM_COOKIE = Get-Content -Raw "$HOME\Downloads\cookies.txt"

.\apps\credential-vault\run.ps1 put `
  --vault $vault `
  --credential-id douyin-main `
  --provider douyin `
  --label "Main creator account" `
  --secret-env VIDEO_PLATFORM_COOKIE `
  --json

$env:VIDEO_PLATFORM_COOKIE = $null
```

Repeating the same write returns `DUPLICATE_COMPLETED`. A changed secret returns `REJECTED_CONFLICT`; use `rotate` to make deliberate replacement visible.

## Inspect, rotate and revoke

```powershell
.\apps\credential-vault\run.ps1 describe --vault $vault --credential-id douyin-main --json

$env:VIDEO_PLATFORM_COOKIE = Get-Content -Raw "$HOME\Downloads\new-cookies.txt"
.\apps\credential-vault\run.ps1 rotate --vault $vault --credential-id douyin-main --secret-env VIDEO_PLATFORM_COOKIE --json
$env:VIDEO_PLATFORM_COOKIE = $null

.\apps\credential-vault\run.ps1 revoke --vault $vault --credential-id douyin-main --json
```

`describe`, `put`, `rotate` and `revoke` never return ciphertext or plaintext. Revocation replaces the encrypted payload with `null`, retains only audit metadata and blocks later resolution.

## Inject into one adapter process

```powershell
$args = @(
  "run", "--vault", $vault,
  "--credential-id", "douyin-main",
  "--expected-provider", "douyin",
  "--target-env", "DOUYIN_COOKIE",
  "--executable", "python",
  "--argument=-m",
  "--argument", "your_platform_adapter"
)
& .\apps\credential-vault\run.ps1 @args
```

The child is started with an argv array and `shell=False`; the secret is added only to `DOUYIN_COOKIE` in the child environment. Existing parent environment variables are inherited normally, so callers should clear temporary secret variables immediately after `put` or `rotate`.

## Security boundary

- DPAPI is CurrentUser scoped; the machine-wide flag is never enabled.
- Credential ID is supplied as DPAPI optional entropy, so ciphertext cannot be moved to another record and resolved there.
- `--expected-provider` rejects a credential/platform mismatch before decryption and child launch.
- Protection is non-interactive and the native output buffer is released after every call.
- Plaintext hashes are not persisted because low-entropy tokens should not gain an offline guessing oracle.
- The JSON registry is atomic but does not provide multi-process locking, backup, ACL provisioning or remote portability.
- A user or process already able to run code as the same Windows account remains inside the local trust boundary.

For production hosting, replace this adapter with a remote KMS/secret-manager owner while retaining redacted credential references at the workflow boundary.
