param(
    [int]$Port = 8775,
    [string]$WorkRoot = (Join-Path $env:TEMP ("MultiWorkspaceStudioLive-" + [guid]::NewGuid().ToString("N")))
)

$ErrorActionPreference = "Stop"
$repository = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$accessLauncher = Join-Path $repository "apps\workspace-access\run.ps1"
$storageLauncher = Join-Path $repository "apps\workspace-storage\run.ps1"
$studioLauncher = Join-Path $repository "apps\video-graph-studio\run.ps1"
$accessRegistry = Join-Path $WorkRoot "workspace-access.json"
$storageRegistry = Join-Path $WorkRoot "workspace-storage.json"
$storageRoot = Join-Path $WorkRoot "storage"
$stdout = Join-Path $WorkRoot "studio.out.log"
$stderr = Join-Path $WorkRoot "studio.err.log"
$serverProcess = $null
$gitCommon = (& git -C $repository rev-parse --git-common-dir).Trim()
$commonPath = if ([IO.Path]::IsPathRooted($gitCommon)) { (Resolve-Path $gitCommon).Path } else { (Resolve-Path (Join-Path $repository $gitCommon)).Path }
$python = Join-Path (Split-Path -Parent $commonPath) "tools\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) { $python = (Get-Command python -ErrorAction Stop).Source }

function Invoke-JsonLauncher {
    param([string]$Launcher, [string[]]$LauncherArguments)
    $lines = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Launcher @LauncherArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Launcher failed with exit code $LASTEXITCODE`: $Launcher $($LauncherArguments -join ' ')"
    }
    return @($lines)[-1] | ConvertFrom-Json
}

function Invoke-StudioJson {
    param(
        [string]$BaseUrl,
        [string]$WorkspaceId,
        [string]$Token,
        [string]$Method,
        [string]$Path,
        $Body
    )
    $headers = @{
        "X-Workspace-Id" = $WorkspaceId
        "Authorization" = "Bearer $Token"
    }
    $request = @{
        Uri = "$BaseUrl$Path"
        Method = $Method
        Headers = $headers
        TimeoutSec = 10
    }
    if ($null -ne $Body) {
        $request.ContentType = "application/json"
        $request.Body = $Body | ConvertTo-Json -Depth 12 -Compress
    }
    return Invoke-RestMethod @request
}

New-Item -ItemType Directory -Path $WorkRoot -Force | Out-Null
$previous = Get-Location
try {
    Set-Location $repository
    if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $Port is already in use."
    }

    foreach ($workspaceId in @("alpha", "beta")) {
        Invoke-JsonLauncher $accessLauncher @(
            "init", "--registry", $accessRegistry,
            "--workspace-id", $workspaceId,
            "--display-name", "Studio $workspaceId",
            "--allowed-root", $repository,
            "--json"
        ) | Out-Null
        Invoke-JsonLauncher $storageLauncher @(
            "provision", "--registry", $storageRegistry,
            "--workspace-id", $workspaceId,
            "--storage-root", $storageRoot,
            "--quota-bytes", "100000000",
            "--json"
        ) | Out-Null
    }

    $alphaIssued = Invoke-JsonLauncher $accessLauncher @(
        "issue", "--registry", $accessRegistry,
        "--workspace-id", "alpha", "--label", "browser-alpha",
        "--scope", "runs:read", "--scope", "runs:write", "--scope", "artifacts:read",
        "--ttl-hours", "1", "--json"
    )
    $betaIssued = Invoke-JsonLauncher $accessLauncher @(
        "issue", "--registry", $accessRegistry,
        "--workspace-id", "beta", "--label", "browser-beta",
        "--scope", "runs:read", "--scope", "runs:write", "--scope", "artifacts:read",
        "--ttl-hours", "1", "--json"
    )

    $studioArguments = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$studioLauncher`"",
        "-NoBrowser", "-Port", "$Port",
        "-AccessRegistry", "`"$accessRegistry`"",
        "-StorageRegistry", "`"$storageRegistry`""
    )
    $serverProcess = Start-Process powershell.exe `
        -ArgumentList $studioArguments `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -PassThru

    $baseUrl = "http://127.0.0.1:$Port"
    $deadline = [DateTime]::UtcNow.AddSeconds(20)
    $health = $null
    do {
        Start-Sleep -Milliseconds 200
        try {
            $health = Invoke-RestMethod -Uri "$baseUrl/api/v1/health" -Method Get -TimeoutSec 2
        } catch {
            $health = $null
        }
    } while ($null -eq $health -and [DateTime]::UtcNow -lt $deadline)
    if ($null -eq $health) {
        $detail = if (Test-Path -LiteralPath $stderr) { Get-Content -LiteralPath $stderr -Raw } else { "" }
        throw "Studio did not start: $detail"
    }

    $createCommand = @{
        contractId = "CMD-RUN-CREATE"
        contractVersion = "1.0"
        operationId = "same-operation"
        correlationId = "same-correlation"
        payload = @{
            sourceRoot = $repository
            languages = @("ru-RU")
            voice = "ru-RU-DmitryNeural"
            platforms = @("local")
        }
    }
    $alphaRun = Invoke-StudioJson $baseUrl "alpha" $alphaIssued.value.token "POST" "/api/v1/runs" $createCommand
    $betaRun = Invoke-StudioJson $baseUrl "beta" $betaIssued.value.token "POST" "/api/v1/runs" $createCommand
    $alphaList = Invoke-StudioJson $baseUrl "alpha" $alphaIssued.value.token "GET" "/api/v1/runs" $null
    $betaList = Invoke-StudioJson $baseUrl "beta" $betaIssued.value.token "GET" "/api/v1/runs" $null

    $crossWorkspaceStatus = $null
    try {
        Invoke-StudioJson $baseUrl "beta" $alphaIssued.value.token "GET" "/api/v1/runs" $null | Out-Null
        $crossWorkspaceStatus = 200
    } catch {
        $crossWorkspaceStatus = [int]$_.Exception.Response.StatusCode
    }
    $finalHealth = Invoke-RestMethod -Uri "$baseUrl/api/v1/health" -Method Get -TimeoutSec 2

    $alphaDatabase = Join-Path $storageRoot "workspaces\alpha\state\video-graph-studio\studio.db"
    $betaDatabase = Join-Path $storageRoot "workspaces\beta\state\video-graph-studio\studio.db"
    $registryText = Get-Content -LiteralPath $accessRegistry -Raw
    $plaintextAbsent = `
        -not $registryText.Contains($alphaIssued.value.token) -and `
        -not $registryText.Contains($betaIssued.value.token)

    $result = [ordered]@{
        workRoot = $WorkRoot
        initialHealth = $health
        finalHealth = $finalHealth
        alphaRunId = $alphaRun.value.runId
        betaRunId = $betaRun.value.runId
        runIdsDiffer = $alphaRun.value.runId -ne $betaRun.value.runId
        alphaRunCount = @($alphaList.runs).Count
        betaRunCount = @($betaList.runs).Count
        crossWorkspaceStatus = $crossWorkspaceStatus
        alphaDatabase = $alphaDatabase
        betaDatabase = $betaDatabase
        plaintextTokensAbsent = $plaintextAbsent
        accessCredentialIds = @($alphaIssued.value.tokenId, $betaIssued.value.tokenId)
    }
} finally {
    if ($null -ne $serverProcess -and -not $serverProcess.HasExited) {
        taskkill /PID $serverProcess.Id /T /F | Out-Null
    }
    Set-Location $previous
}

Start-Sleep -Milliseconds 300
foreach ($database in @($result.alphaDatabase, $result.betaDatabase)) {
    & $python -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute('PRAGMA wal_checkpoint(TRUNCATE)'); c.close()" $database
    if ($LASTEXITCODE -ne 0) { throw "SQLite checkpoint failed: $database" }
}
$result["alphaDatabaseSha256"] = (Get-FileHash -LiteralPath $result.alphaDatabase -Algorithm SHA256).Hash.ToLowerInvariant()
$result["betaDatabaseSha256"] = (Get-FileHash -LiteralPath $result.betaDatabase -Algorithm SHA256).Hash.ToLowerInvariant()
$result.Remove("alphaDatabase")
$result.Remove("betaDatabase")
$result.portClosed = -not [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
$result | ConvertTo-Json -Depth 10
