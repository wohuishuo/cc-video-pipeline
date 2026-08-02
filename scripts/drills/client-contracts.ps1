$ErrorActionPreference="Stop"
$repository=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$launcher=Join-Path $repository "apps\client-contracts\run.ps1"
$drill=Join-Path $env:TEMP ("client-contracts-drill-"+[guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $drill | Out-Null
try {
  $bundle=Join-Path $drill "contracts.json"; $command=Join-Path $drill "command.json"
  [IO.File]::WriteAllText($command,'{"contractId":"CMD-RUN-START","contractVersion":"1.0","operationId":"mobile-start-1","correlationId":"mobile-corr-1","payload":{}}',[Text.UTF8Encoding]::new($false))
  $export=& $launcher export --output $bundle --json | ConvertFrom-Json
  $validate=& $launcher validate-command --input $command --expected-contract CMD-RUN-START --json | ConvertFrom-Json
  $compatible=& $launcher check-client --client-version 1.2.0 --json | ConvertFrom-Json
  $result=[pscustomobject]@{Export=$export.resultClass;Validation=$validate.resultClass;Compatibility=$compatible.resultClass;BundleSha256=(Get-FileHash -Algorithm SHA256 $bundle).Hash.ToLowerInvariant()}
  $result|ConvertTo-Json
  if ($result.Export -ne "COMPLETED" -or $result.Validation -ne "VALID" -or $result.Compatibility -ne "COMPATIBLE") { throw "Client Contracts drill failed." }
} finally { if(Test-Path $drill){Remove-Item -LiteralPath $drill -Recurse -Force} }
