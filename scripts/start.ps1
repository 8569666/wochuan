param([switch]$TestMode)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$cachePath = Join-Path $projectRoot '.cache'
New-Item -ItemType Directory -Force -Path $cachePath | Out-Null
$modeName = if ($TestMode) { 'test' } else { 'dev' }
$apiPort = if ($TestMode) { 8001 } else { 8000 }
$frontPort = if ($TestMode) { 5174 } else { 5173 }
$stateFile = Join-Path $cachePath "processes.$modeName.json"
if (Test-Path -LiteralPath $stateFile) {
    $existingState = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
    if (Get-Process -Id $existingState.BackendId -ErrorAction SilentlyContinue) {
        throw '记录中的后台仍在运行，请先执行 scripts/stop.ps1（测试模式加 -TestMode）。'
    }
}
foreach ($portToCheck in @($apiPort, $frontPort)) {
    $probe = [System.Net.Sockets.TcpClient]::new()
    try {
        $probe.Connect('127.0.0.1', $portToCheck)
        if ($probe.Connected) { throw "端口 $portToCheck 已被占用，请先关闭对应服务。" }
    } catch [System.Net.Sockets.SocketException] {
        # No listener: the port is available.
    } finally { $probe.Dispose() }
}
$pythonPath = Join-Path $projectRoot '.venv/Scripts/python.exe'
$nodePath = (Get-Command node -ErrorAction Stop).Source
$vitePath = Join-Path $projectRoot 'frontend/node_modules/vite/bin/vite.js'
if (!(Test-Path -LiteralPath $pythonPath) -or !(Test-Path -LiteralPath $vitePath)) { throw '请先运行 scripts/setup.ps1。' }
$previousDatabase = $env:MYSQL_DATABASE
$previousOrigin = $env:APP_ORIGIN
$previousTarget = $env:API_TARGET
$previousUtf8 = $env:PYTHONUTF8
try {
    if ($TestMode) { $env:MYSQL_DATABASE = 'codex_werp_test' }
    $env:APP_ORIGIN = "http://127.0.0.1:$frontPort"
    $env:API_TARGET = "http://127.0.0.1:$apiPort"
    $env:PYTHONUTF8 = '1'
    $backendProcess = Start-Process -FilePath $pythonPath -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port', $apiPort) -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $cachePath "backend.$modeName.log") -RedirectStandardError (Join-Path $cachePath "backend.$modeName.error.log")
    $frontendProcess = Start-Process -FilePath $nodePath -ArgumentList @('"' + $vitePath + '"','--host','127.0.0.1','--port',$frontPort,'--strictPort') -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $cachePath "frontend.$modeName.log") -RedirectStandardError (Join-Path $cachePath "frontend.$modeName.error.log")
    @{BackendId=$backendProcess.Id;FrontendId=$frontendProcess.Id;BackendStarted=$backendProcess.StartTime.ToUniversalTime().Ticks;FrontendStarted=$frontendProcess.StartTime.ToUniversalTime().Ticks;PythonPath=$pythonPath;NodePath=$nodePath} | ConvertTo-Json | Set-Content -LiteralPath $stateFile -Encoding utf8
    Write-Output "后台已启动：http://127.0.0.1:$frontPort（API $apiPort）"
} catch {
    if ($backendProcess -and !$backendProcess.HasExited) { Stop-Process -Id $backendProcess.Id }
    throw
} finally {
    $env:MYSQL_DATABASE=$previousDatabase;$env:APP_ORIGIN=$previousOrigin;$env:API_TARGET=$previousTarget;$env:PYTHONUTF8=$previousUtf8
}
