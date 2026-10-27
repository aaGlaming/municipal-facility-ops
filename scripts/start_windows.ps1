param(
    [ValidateSet('backend', 'frontend', 'chroma', 'mysql', 'all')]
    [string]$Component = 'all',
    [switch]$SkipNpmInstall
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Ensure-EnvFile {
    if (-not (Test-Path -LiteralPath 'backend/.env')) {
        Copy-Item -LiteralPath 'backend/.env.example' -Destination 'backend/.env'
        Write-Host '已创建 backend/.env，请按本机 MySQL 和模型配置检查变量。' -ForegroundColor Yellow
    }
    if (-not (Test-Path -LiteralPath 'frontend/.env')) {
        Copy-Item -LiteralPath 'frontend/.env.example' -Destination 'frontend/.env'
    }
}

function Start-Backend {
    Ensure-EnvFile
    $env:PYTHONPATH = 'backend'
    python -m uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000
}

function Start-Frontend {
    if (-not (Test-Path -LiteralPath 'frontend/node_modules') -and -not $SkipNpmInstall) {
        npm --prefix frontend ci
    }
    npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173
}

function Start-Chroma {
    New-Item -ItemType Directory -Force -Path '.chroma' | Out-Null
    $chroma = Get-Command chroma -ErrorAction SilentlyContinue
    if ($chroma) {
        & $chroma.Source run --path '.chroma' --host 127.0.0.1 --port 8001
    } else {
        python -m chromadb.cli.cli run --path '.chroma' --host 127.0.0.1 --port 8001
    }
}

function Start-MySql {
    $service = Get-Service -Name 'MySQL84' -ErrorAction SilentlyContinue
    if (-not $service) {
        throw '未找到 MySQL84 Windows 服务。请先安装 MySQL 8.4，并创建 municipal_ops 数据库及 municipal 用户。'
    }
    if ($service.Status -ne 'Running') {
        Start-Service -Name 'MySQL84'
        Write-Host 'MySQL84 已启动。'
    } else {
        Write-Host 'MySQL84 已在运行。'
    }
}

switch ($Component) {
    'backend' { Start-Backend }
    'frontend' { Start-Frontend }
    'chroma' { Start-Chroma }
    'mysql' { Start-MySql }
    'all' {
        Write-Host '请在 IDE 的独立终端分别运行 backend、frontend、chroma；MySQL 先运行 mysql。' -ForegroundColor Cyan
        Write-Host '示例：powershell -ExecutionPolicy Bypass -File scripts/start_windows.ps1 -Component backend'
        Write-Host '当前终端只启动 MySQL 服务，避免多个前台进程互相阻塞。'
        Start-MySql
    }
}
