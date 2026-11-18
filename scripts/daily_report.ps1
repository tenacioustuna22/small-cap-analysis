# Daily report run for Windows Task Scheduler (task "Stock analysis daily report",
# weekdays 1:15 pm Pacific, 15 minutes after the US close).
# Refreshes prices and EDGAR data, rewrites today's reports, and appends the output to
# data\logs\daily_report.log (git-ignored).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
$logDir = Join-Path $root "data\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir "daily_report.log"

"==== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ====" | Out-File -FilePath $log -Append -Encoding utf8
& (Join-Path $root ".venv\Scripts\python.exe") (Join-Path $root "scripts\report.py") --refresh *>&1 |
    Out-File -FilePath $log -Append -Encoding utf8
$code = $LASTEXITCODE
"exit code $code" | Out-File -FilePath $log -Append -Encoding utf8
exit $code
