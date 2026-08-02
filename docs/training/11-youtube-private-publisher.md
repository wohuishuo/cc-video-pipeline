# Tutorial: private YouTube Publisher

## 1. Understand the credential boundary

Create Google OAuth credentials with YouTube upload permission and obtain either a temporary `accessToken` or the refreshable JSON fields `clientId`, `clientSecret`, `refreshToken`. Put the complete JSON string into Credential Vault; never put it in a plan, metadata file or command argument.

## 2. Verify the independent application

```powershell
powershell -ExecutionPolicy Bypass -File .\apps\youtube-publisher\run.ps1 doctor --json
python -m pytest --import-mode=importlib tests\youtube_publisher_mvp -q
```

## 3. Use the guarded composition

Create a private YouTube Publication plan that names the YouTube credential ID. In Video Graph Studio, run **Publish Plan**, copy its committed SHA-256, then run **Publish Execute** with the same plan run, exact SHA and Credential Vault path. Publication asks the vault to inject the credential into Platform I/O; Platform I/O selects YouTube Publisher.

## 4. Interpret the result

- `COMPLETED` requires a non-empty YouTube video ID and private visibility.
- `DUPLICATE_COMPLETED` reuses the matching committed receipt without network access.
- `UNKNOWN` means a session existed but completion could not be proven; automatic replay is blocked to avoid duplicates.

The current automated suite proves the composition with substitutes. A real channel remains untouched until its owner deliberately supplies OAuth credentials and executes a private upload.
