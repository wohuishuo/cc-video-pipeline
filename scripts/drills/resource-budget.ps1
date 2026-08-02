$ErrorActionPreference = "Stop"
$repository = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$storageLauncher = Join-Path $repository "apps\workspace-storage\run.ps1"
$budgetLauncher = Join-Path $repository "apps\resource-budget\run.ps1"
$drill = Join-Path $env:TEMP ("resource-budget-drill-" + [guid]::NewGuid().ToString("N"))
$storageRegistry = Join-Path $drill "storage.json"
$storageRoot = Join-Path $drill "storage"
$budgetDatabase = Join-Path $drill "budget.db"
New-Item -ItemType Directory -Path $drill | Out-Null
try {
  $provision = & $storageLauncher provision --registry $storageRegistry --workspace-id alpha --storage-root $storageRoot --quota-bytes 1000 --json | ConvertFrom-Json
  $artifact = Join-Path $provision.value.roots.artifacts "existing.bin"
  [IO.File]::WriteAllBytes($artifact, (New-Object byte[] 200))
  $capacity = & $storageLauncher capacity --registry $storageRegistry --workspace-id alpha --required-bytes 0 --json | ConvertFrom-Json
  $available = [int64]$capacity.value.availableBytes
  $configure = & $budgetLauncher configure --database $budgetDatabase --workspace-id alpha --byte-limit $available --execution-slots 1 --json | ConvertFrom-Json
  $first = & $budgetLauncher reserve --database $budgetDatabase --workspace-id alpha --reservation-id run-one --bytes 600 --slots 1 --ttl-seconds 60 --json | ConvertFrom-Json
  $deniedText = & $budgetLauncher reserve --database $budgetDatabase --workspace-id alpha --reservation-id run-two --bytes 300 --slots 0 --ttl-seconds 60 --json
  $deniedCode = $LASTEXITCODE; $denied = $deniedText | ConvertFrom-Json
  $released = & $budgetLauncher release --database $budgetDatabase --workspace-id alpha --reservation-id run-one --expected-generation 1 --json | ConvertFrom-Json
  $second = & $budgetLauncher reserve --database $budgetDatabase --workspace-id alpha --reservation-id run-three --bytes $available --slots 1 --ttl-seconds 60 --json | ConvertFrom-Json
  $snapshot = & $budgetLauncher snapshot --database $budgetDatabase --workspace-id alpha --json | ConvertFrom-Json
  $result = [pscustomobject]@{
    StorageUsageBytes = $capacity.value.usageBytes
    StorageAvailableBytes = $available
    Configure = $configure.resultClass
    FirstReserve = $first.resultClass
    DeniedReserve = $denied.resultClass
    DeniedExitCode = $deniedCode
    Release = $released.resultClass
    ReplacementReserve = $second.resultClass
    ReservedBytes = $snapshot.value.reservedBytes
    ReservedSlots = $snapshot.value.reservedSlots
    ActiveReservations = $snapshot.value.activeReservations
    DatabaseSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $budgetDatabase).Hash.ToLowerInvariant()
  }
  $result | ConvertTo-Json
  if ($result.StorageUsageBytes -ne 200 -or $available -ne 800 -or $result.FirstReserve -ne "COMPLETED" -or $result.DeniedReserve -ne "REJECTED_BUDGET" -or $deniedCode -ne 3 -or $result.Release -ne "COMPLETED" -or $result.ReplacementReserve -ne "COMPLETED" -or $result.ReservedBytes -ne 800 -or $result.ReservedSlots -ne 1 -or $result.ActiveReservations -ne 1) { throw "Resource Budget drill failed." }
} finally {
  if (Test-Path -LiteralPath $drill) { Remove-Item -LiteralPath $drill -Recurse -Force }
}
