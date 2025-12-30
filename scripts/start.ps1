# AI语言学习系统 - 快速启动脚本

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "AI 语言学习系统 - 启动中..." -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

# 1. 停止可能运行的进程
Write-Host "`n[1/3] 清理旧进程..." -ForegroundColor Yellow
Stop-Process -Name node -Force -ErrorAction SilentlyContinue
Get-Process python -ErrorAction SilentlyContinue | Where-Object { 
    $_.CommandLine -like "*http.server*" 
} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
Write-Host "✓ 进程清理完成" -ForegroundColor Green

# 2. 启动后端服务器
Write-Host "`n[2/3] 启动后端服务器..." -ForegroundColor Yellow
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
$rootPath = Split-Path -Parent $scriptPath
$backendPath = Join-Path $rootPath "backend"

Start-Process powershell -ArgumentList `
    "-NoExit", `
    "-Command", `
    "cd '$backendPath'; Write-Host '后端服务器启动中...' -ForegroundColor Cyan; npx tsx src/index.ts"
Write-Host "✓ 后端服务器已在新窗口启动" -ForegroundColor Green
Start-Sleep -Seconds 3

# 3. 启动前端 HTTP 服务器
Write-Host "`n[3/3] 启动前端服务器..." -ForegroundColor Yellow
$frontendPath = Join-Path $rootPath "app\src\renderer"
Start-Process powershell -ArgumentList `
    "-NoExit", `
    "-Command", `
    "cd '$frontendPath'; Write-Host '前端服务器启动中...' -ForegroundColor Cyan; python -m http.server 8000"
Write-Host "✓ 前端服务器已在新窗口启动" -ForegroundColor Green
Start-Sleep -Seconds 2

# 4. 打开浏览器
Write-Host "`n[完成] 打开浏览器..." -ForegroundColor Yellow
Start-Process "http://localhost:8000/voice-dialogue.html"
Write-Host "✓ 浏览器已打开" -ForegroundColor Green

Write-Host "`n" + "=" * 60 -ForegroundColor Cyan
Write-Host "系统启动完成！" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "`n服务地址：" -ForegroundColor White
Write-Host "  • 后端 API:    http://localhost:3000" -ForegroundColor White
Write-Host "  • 前端页面:    http://localhost:8000/voice-dialogue.html" -ForegroundColor White
Write-Host "  • WebSocket:   ws://localhost:3000/stream" -ForegroundColor White
Write-Host "`n提示：按 Ctrl+C 可关闭此脚本窗口" -ForegroundColor Gray
Write-Host ""
