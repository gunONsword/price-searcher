$ErrorActionPreference = 'Stop'
$projectPath = Split-Path $PSScriptRoot -Parent
& (Join-Path $projectPath 'start-local.ps1')
$logPath = Join-Path $projectPath '.local\collection-logs'
New-Item -ItemType Directory -Force $logPath | Out-Null
$logFile = Join-Path $logPath ((Get-Date -Format 'yyyy-MM-dd-HHmmss') + '.log')
& (Join-Path $projectPath '.venv\Scripts\python.exe') -X utf8 (Join-Path $PSScriptRoot 'collect_all_scheduled.py') *> $logFile
exit $LASTEXITCODE
