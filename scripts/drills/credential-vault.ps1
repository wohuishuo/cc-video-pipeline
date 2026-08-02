$ErrorActionPreference = "Stop"
$repository = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$launcher = Join-Path $repository "apps\credential-vault\run.ps1"
$gitCommon = (& git -C $repository rev-parse --git-common-dir).Trim()
$commonPath = if ([IO.Path]::IsPathRooted($gitCommon)) { (Resolve-Path $gitCommon).Path } else { (Resolve-Path (Join-Path $repository $gitCommon)).Path }
$python = Join-Path (Split-Path -Parent $commonPath) "tools\.venv\Scripts\python.exe"
$drill = Join-Path $env:TEMP ("credential-vault-drill-" + [guid]::NewGuid().ToString("N"))
$vault = Join-Path $drill "vault.json"
$secret = "cv-real-drill-20260802-only-child"
$expectedHash = "74accbcc50d1800a742f1ed0f3f6bbb44d969509a9857472af121774aabf25a9"

New-Item -ItemType Directory -Path $drill | Out-Null
try {
  $env:CV_DRILL_SECRET = $secret
  $put = & $launcher put --vault $vault --credential-id youtube-main --provider youtube --label "Main channel" --secret-env CV_DRILL_SECRET --json
  $putCode = $LASTEXITCODE
  $replay = & $launcher put --vault $vault --credential-id youtube-main --provider youtube --label "Main channel" --secret-env CV_DRILL_SECRET --json
  $replayCode = $LASTEXITCODE
  $env:CV_DRILL_SECRET = $null

  $describe = & $launcher describe --vault $vault --credential-id youtube-main --json
  $describeCode = $LASTEXITCODE
  $childScript = "import hashlib,os,sys; value=os.environ.get('PLATFORM_SECRET',''); sys.exit(0 if hashlib.sha256(value.encode()).hexdigest() == '$expectedHash' else 11)"
  $runArguments = @("run", "--vault", $vault, "--credential-id", "youtube-main", "--target-env", "PLATFORM_SECRET", "--executable", $python, "--argument=-c", "--argument", $childScript)
  & $launcher @runArguments
  $childCode = $LASTEXITCODE

  $persisted = Get-Content -Raw -LiteralPath $vault
  $leaked = $persisted.Contains($secret) -or $put.Contains($secret) -or $replay.Contains($secret) -or $describe.Contains($secret)
  $sha = (Get-FileHash -Algorithm SHA256 -LiteralPath $vault).Hash.ToLowerInvariant()
  $result = [pscustomobject]@{
    PutCode = $putCode
    PutResult = ($put | ConvertFrom-Json).resultClass
    ReplayCode = $replayCode
    ReplayResult = ($replay | ConvertFrom-Json).resultClass
    DescribeCode = $describeCode
    DescribeStatus = ($describe | ConvertFrom-Json).value.status
    ChildCode = $childCode
    PlaintextLeak = $leaked
    VaultSha256 = $sha
  }
  $result | ConvertTo-Json
  if ($putCode -ne 0 -or $replayCode -ne 0 -or $describeCode -ne 0 -or $childCode -ne 0 -or $leaked) {
    throw "Credential Vault drill failed."
  }
} finally {
  $env:CV_DRILL_SECRET = $null
  if (Test-Path -LiteralPath $drill) { Remove-Item -LiteralPath $drill -Recurse -Force }
}
