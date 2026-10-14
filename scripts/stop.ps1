param([switch]$TestMode)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$modeName = if ($TestMode) { 'test' } else { 'dev' }
$stateFile = Join-Path $projectRoot ".cache/processes.$modeName.json"
if (!(Test-Path -LiteralPath $stateFile)) { Write-Output '没有记录中的项目进程。'; return }
$state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
foreach ($name in @('Backend','Frontend')) {
    $recordedId = $state."${name}Id"
    $recordedTime = $state."${name}Started"
    $expectedPath = if ($name -eq 'Backend') { $state.PythonPath } else { $state.NodePath }
    $processToStop = Get-Process -Id $recordedId -ErrorAction SilentlyContinue
    if ($processToStop -and $processToStop.StartTime.ToUniversalTime().Ticks -eq $recordedTime -and $processToStop.Path -eq $expectedPath) { Stop-Process -Id $recordedId }
    elseif ($processToStop) { throw '进程身份已变化，已拒绝停止其他进程。' }
}
Remove-Item -LiteralPath $stateFile
Write-Output '项目进程已停止。'
