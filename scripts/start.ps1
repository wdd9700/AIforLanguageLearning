<#
AI 外语学习系统 - 快速启动脚本

目标：启动“既定技术路线”的开发组合：
- 后端：backend_fastapi (FastAPI) 监听 8012
- 前端：app/v5 (Vite) 监听 5173

原则：控制台输出必须与实际状态一致。
- 只有在端口监听 / HTTP 健康检查通过后才打印 ✓
- 不盲目 Stop-Process -Name node/python（避免误杀其它开发进程）
#>

param(
    [int]$BackendPort = 8012,
    [int]$FrontendPort = 5173,
    [switch]$SkipBrowser
)

$ErrorActionPreference = 'Stop'

function Write-Step([string]$text) {
    Write-Host ("`n" + $text) -ForegroundColor Yellow
}

function Write-Ok([string]$text) {
    Write-Host ("✓ " + $text) -ForegroundColor Green
}

function Write-Warn([string]$text) {
    Write-Host ("! " + $text) -ForegroundColor Yellow
}

function Write-Fail([string]$text) {
    Write-Host ("✗ " + $text) -ForegroundColor Red
}

function Test-PortListening([int]$port) {
    try {
        $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction Stop
        return ($null -ne $conns)
    } catch {
        return $false
    }
}

function Wait-HttpOk([string]$url, [int]$timeoutSeconds = 25) {
    $start = Get-Date
    while (((Get-Date) - $start).TotalSeconds -lt $timeoutSeconds) {
        try {
            $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) {
                return $true
            }
        } catch {
            # Some PowerShell versions throw on non-2xx. If we still got an HTTP response,
            # consider the server reachable.
            try {
                $resp = $_.Exception.Response
                if ($null -ne $resp -and $resp.StatusCode) {
                    $code = [int]$resp.StatusCode
                    if ($code -ge 200 -and $code -lt 500) {
                        return $true
                    }
                }
            } catch {
                # ignore
            }
            Start-Sleep -Milliseconds 400
        }
    }
    return $false
}

function Wait-HttpOkAny([string[]]$urls, [int]$timeoutSeconds = 25) {
    $start = Get-Date
    while (((Get-Date) - $start).TotalSeconds -lt $timeoutSeconds) {
        foreach ($u in $urls) {
            if (Wait-HttpOk -url $u -timeoutSeconds 1) {
                return $u
            }
        }
        Start-Sleep -Milliseconds 250
    }
    return $null
}

Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "AI 外语学习系统 - 启动中..." -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
$rootPath = Split-Path -Parent $scriptPath
$backendFastApiPath = Join-Path $rootPath "backend_fastapi"
$frontendV5Path = Join-Path $rootPath "app\v5"
$pidDir = Join-Path $rootPath ".tmp\pids"
$backendPidFile = Join-Path $pidDir "backend_fastapi_pwsh.pid"
$frontendPidFile = Join-Path $pidDir "frontend_v5_pwsh.pid"

New-Item -ItemType Directory -Force -Path $pidDir | Out-Null

Write-Step "[1/3] 环境与端口检查"
if (-not (Test-Path $backendFastApiPath)) {
    throw "backend_fastapi 目录不存在：$backendFastApiPath"
}
if (-not (Test-Path $frontendV5Path)) {
    throw "app/v5 目录不存在：$frontendV5Path"
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "未找到 python。请先安装 Python，或在当前终端激活你的虚拟环境/conda 环境后重试。"
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "未找到 npm。请先安装 Node.js（含 npm），或确保 npm 在 PATH。"
}

if (Test-PortListening -port $BackendPort) {
    Write-Warn "端口 $BackendPort 已在监听。将跳过启动 FastAPI，并改为做健康检查。"
}
if (Test-PortListening -port $FrontendPort) {
    Write-Warn "端口 $FrontendPort 已在监听。将跳过启动前端，并改为做连通性检查。"
}

Write-Ok "基础检查完成"

Write-Step "[2/3] 启动后端 (FastAPI)"
if (-not (Test-PortListening -port $BackendPort)) {
    $backendCmd = "cd '$backendFastApiPath'; Write-Host 'FastAPI 后端启动中...' -ForegroundColor Cyan; python -m uvicorn app.main:app --reload --host 127.0.0.1 --port $BackendPort"
    $backendProc = Start-Process pwsh -PassThru -ArgumentList "-NoExit", "-Command", $backendCmd
    Set-Content -Path $backendPidFile -Value $backendProc.Id
    Write-Host "已启动后端窗口（PID=$($backendProc.Id)），等待健康检查..." -ForegroundColor Gray
}

$healthUrl = "http://127.0.0.1:$BackendPort/health"
if (Wait-HttpOk -url $healthUrl -timeoutSeconds 35) {
    Write-Ok "后端可用：$healthUrl"
} else {
    Write-Fail "后端健康检查失败：$healthUrl"
    Write-Host "建议：查看后端窗口输出；确认依赖已安装（backend_fastapi/pyproject.toml）并且端口未被占用。" -ForegroundColor Gray
    throw "后端未就绪，停止继续启动前端。"
}

Write-Step "[3/3] 启动前端 (Vite / app/v5)"
if (-not (Test-PortListening -port $FrontendPort)) {
    $frontendCmd = "cd '$frontendV5Path'; Write-Host 'Vite 前端启动中...' -ForegroundColor Cyan; npm run dev"
    $frontendProc = Start-Process pwsh -PassThru -ArgumentList "-NoExit", "-Command", $frontendCmd
    Set-Content -Path $frontendPidFile -Value $frontendProc.Id
    Write-Host "已启动前端窗口（PID=$($frontendProc.Id)），等待连通性检查..." -ForegroundColor Gray
}

$frontendUrl = "http://127.0.0.1:$FrontendPort"
$frontendCandidates = @(
    "http://localhost:$FrontendPort",
    "http://127.0.0.1:$FrontendPort",
    "http://[::1]:$FrontendPort"
)
$frontendReadyUrl = Wait-HttpOkAny -urls $frontendCandidates -timeoutSeconds 75
if ($frontendReadyUrl) {
    $frontendUrl = $frontendReadyUrl
    Write-Ok "前端可用：$frontendUrl"
} else {
    Write-Fail "前端连通性检查失败：$frontendUrl"
    Write-Host "建议：查看前端窗口输出；首次启动需要在 app/v5 下执行 npm install。" -ForegroundColor Gray
    throw "前端未就绪。"
}

if (-not $SkipBrowser) {
    Write-Step "[完成] 打开浏览器"
    Start-Process $frontendUrl
    Write-Ok "已打开：$frontendUrl"
}

Write-Host ("`n" + "=" * 60) -ForegroundColor Cyan
Write-Host "系统启动完成（已验证可用）" -ForegroundColor Green
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "`n服务地址：" -ForegroundColor White
Write-Host "  • 后端 API:    http://127.0.0.1:$BackendPort" -ForegroundColor White
Write-Host "  • 前端页面:    $frontendUrl" -ForegroundColor White
Write-Host "  • WebSocket:   ws://127.0.0.1:$BackendPort/ws/v1" -ForegroundColor White
Write-Host "`n提示：本脚本不会强制杀进程；如需停止服务，请关闭各自的新窗口。" -ForegroundColor Gray
