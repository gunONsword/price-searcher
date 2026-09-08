$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
& 'C:\Users\gos\project\.local\searchers-postgresql\start-db.ps1'
$runtimePath = Join-Path $PSScriptRoot '.local'
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$appPath = Join-Path $PSScriptRoot 'price_searcher'
if (-not (Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue)) {
    $web = Start-Process -FilePath $pythonPath -ArgumentList 'serve_local.py' -WorkingDirectory $appPath -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimePath 'web.stdout.log') -RedirectStandardError (Join-Path $runtimePath 'web.stderr.log')
    $web.Id | Set-Content (Join-Path $runtimePath 'web.pid')
}
$cloudflaredPath = 'C:\Program Files (x86)\cloudflared\cloudflared.exe'
$tunnelConfig = Join-Path $runtimePath 'tunnel.yml'
$existingTunnel = Get-CimInstance Win32_Process -Filter "name='cloudflared.exe'" | Where-Object { $_.CommandLine -like "*$tunnelConfig*" }
if (-not $existingTunnel) {
    $tunnel = Start-Process -FilePath $cloudflaredPath -ArgumentList "tunnel --config `"$tunnelConfig`" run hardware-price-tunnel" -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimePath 'tunnel.stdout.log') -RedirectStandardError (Join-Path $runtimePath 'tunnel.stderr.log')
    $tunnel.Id | Set-Content (Join-Path $runtimePath 'tunnel.pid')
}
Write-Output 'Services started: https://hardware-price.gunonsword-ai.com'
