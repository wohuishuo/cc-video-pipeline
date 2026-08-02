param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
$sha = [Security.Cryptography.SHA256]::Create()
try {
  $bytes = [Text.Encoding]::UTF8.GetBytes([string]$env:VIDEO_PLATFORM_CREDENTIAL)
  $actual = ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace("-", "").ToLowerInvariant()
} finally {
  $sha.Dispose()
}
$hasContract = $Arguments -contains "--credential-env" -and $Arguments -contains "VIDEO_PLATFORM_CREDENTIAL"
if ($hasContract -and $actual -eq $env:EXPECTED_CREDENTIAL_SHA256) {
  '{"status":"ok","external_id":"credential-drill-123"}'
  exit 0
}
'{"status":"failed","error":"credential contract mismatch"}'
exit 9
