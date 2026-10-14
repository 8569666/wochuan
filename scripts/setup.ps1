$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    $version = python -c 'import sys; print("%s.%s" % sys.version_info[:2])'
    if ($version -ne '3.14') { throw '本项目需要 Python 3.14。' }
    if (!(Test-Path -LiteralPath '.env')) { throw '请参考 .env.example 配置根目录 .env。' }
    if (!(Test-Path -LiteralPath '.venv/Scripts/python.exe')) { python -m venv .venv; if($LASTEXITCODE){throw '虚拟环境创建失败'} }
    & '.venv/Scripts/python.exe' -m pip install -r backend/requirements.lock
    if ($LASTEXITCODE) { throw '后端依赖安装失败' }
    Push-Location frontend
    try { npm ci --no-audit --no-fund; if ($LASTEXITCODE) { throw '前端依赖安装失败' } } finally { Pop-Location }
    Push-Location backend
    try {
        & '../.venv/Scripts/python.exe' -m app.cli check-db; if($LASTEXITCODE){throw '数据库连接失败'}
        & '../.venv/Scripts/python.exe' -m app.cli migrate; if($LASTEXITCODE){throw '迁移失败'}
        & '../.venv/Scripts/python.exe' -m app.cli init-admin; if($LASTEXITCODE){throw '管理员初始化失败'}
    } finally { Pop-Location }
    Write-Output '初始化完成，运行 scripts/start.ps1 启动。'
} finally { Pop-Location }
