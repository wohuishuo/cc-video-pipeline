$ErrorActionPreference = "Stop"
$repository = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$publication = Join-Path $repository "apps\publication\run.ps1"
$vaultLauncher = Join-Path $repository "apps\credential-vault\run.ps1"
$fakePlatform = Join-Path $repository "scripts\drills\fakes\credential-platform.ps1"
$drill = Join-Path $env:TEMP ("credential-publication-drill-" + [guid]::NewGuid().ToString("N"))
$vault = Join-Path $drill "vault.json"
$video = Join-Path $drill "video.mp4"
$metadata = Join-Path $drill "metadata.json"
$planDirectory = Join-Path $drill "plan"
$runDirectory = Join-Path $drill "run"
$secret = "credential-publication-" + [guid]::NewGuid().ToString("N")

New-Item -ItemType Directory -Path $drill | Out-Null
try {
  [IO.File]::WriteAllBytes($video, [Text.Encoding]::UTF8.GetBytes("verified-video-placeholder"))
  [IO.File]::WriteAllText($metadata, '{"title":"Credential drill"}', [Text.UTF8Encoding]::new($false))
  $sha = [Security.Cryptography.SHA256]::Create()
  try {
    $env:EXPECTED_CREDENTIAL_SHA256 = ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($secret)))).Replace("-", "").ToLowerInvariant()
  } finally {
    $sha.Dispose()
  }

  $env:PUBLICATION_DRILL_SECRET = $secret
  $put = & $vaultLauncher put --vault $vault --credential-id youtube-main --provider youtube --label "Main" --secret-env PUBLICATION_DRILL_SECRET --json
  $putCode = $LASTEXITCODE
  $env:PUBLICATION_DRILL_SECRET = $null

  $planResult = & $publication plan $video --metadata $metadata --target youtube=main --credential youtube=youtube-main --output-dir $planDirectory --operation-id plan-credential-drill --json
  $planCode = $LASTEXITCODE
  $planPayload = $planResult | ConvertFrom-Json
  $planPath = $planPayload.artifact
  $planSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $planPath).Hash.ToLowerInvariant()

  $executeResult = & $publication execute $planPath --confirmation $planSha --credential-vault $vault --platform-io-launcher $fakePlatform --output-dir $runDirectory --operation-id execute-credential-drill --json
  $executeCode = $LASTEXITCODE
  $executePayload = $executeResult | ConvertFrom-Json
  $manifest = Get-Content -Raw -LiteralPath $executePayload.artifact | ConvertFrom-Json
  $captured = $put + $planResult + $executeResult + (Get-Content -Raw -LiteralPath $vault) + (Get-Content -Raw -LiteralPath $planPath) + (Get-Content -Raw -LiteralPath (Join-Path $runDirectory "publication-receipt.json")) + (Get-Content -Raw -LiteralPath $executePayload.artifact)
  $leaked = $captured.Contains($secret)

  $result = [pscustomobject]@{
    PutCode = $putCode
    PlanCode = $planCode
    PlanResult = $planPayload.resultClass
    ExecuteCode = $executeCode
    ExecuteResult = $executePayload.resultClass
    CredentialReference = $manifest.publications[0].facts.credentialReferenceUsed
    ExternalId = $manifest.publications[0].externalId
    MaximumActiveExecutions = (Get-Content -Raw -LiteralPath (Join-Path $runDirectory "publication-receipt.json") | ConvertFrom-Json).maximumActiveExecutions
    PlaintextLeak = $leaked
    PlanSha256 = $planSha
    ManifestSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $executePayload.artifact).Hash.ToLowerInvariant()
  }
  $result | ConvertTo-Json
  if ($putCode -ne 0 -or $planCode -ne 0 -or $executeCode -ne 0 -or $executePayload.resultClass -ne "COMPLETED" -or -not $result.CredentialReference -or $leaked) {
    throw "Credential-aware publication drill failed."
  }
} finally {
  $env:PUBLICATION_DRILL_SECRET = $null
  $env:EXPECTED_CREDENTIAL_SHA256 = $null
  if (Test-Path -LiteralPath $drill) { Remove-Item -LiteralPath $drill -Recurse -Force }
}
