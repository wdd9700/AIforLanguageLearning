<#
快速启动/检查服务（开发）

重要：本仓库当前默认开发路线是 FastAPI（backend_fastapi）+ Vite（app/v5）。
旧的 Node 后端（backend/，默认 3000）属于 legacy，不应再作为默认启动目标。

本脚本只做“真实可验证”的检查：
- FastAPI: /health 与 /api/system/config
- 可选外部服务：LM Studio / OCR / TTS / ASR（仅提示，不伪装已启动）

如果你想一键启动 FastAPI + 前端，请用：.\scripts\start.ps1
#>

param(
    [int]$BackendPort = 8012
)

$ErrorActionPreference = 'Stop'

Write-Host "🚀 AI Language Learning - Service Checker" -ForegroundColor Cyan
Write-Host "=" -NoNewline; for($i=0;$i -lt 60;$i++){Write-Host "=" -NoNewline}; Write-Host ""
Write-Host ""

# 检查 FastAPI 后端是否运行
Write-Host "1️⃣ Checking FastAPI Backend..." -ForegroundColor Yellow
$healthUrl = "http://127.0.0.1:$BackendPort/health"
$configUrl = "http://127.0.0.1:$BackendPort/api/system/config"
try {
    $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 3 -ErrorAction Stop
    Write-Host "   ✅ FastAPI is running: $healthUrl" -ForegroundColor Green
} catch {
    Write-Host "   ❌ FastAPI not reachable: $healthUrl" -ForegroundColor Red
    Write-Host "   👉 Run: .\scripts\start.ps1" -ForegroundColor Yellow
    Write-Host "" 
    throw "Backend not ready"
}

try {
    $cfg = Invoke-RestMethod -Uri $configUrl -TimeoutSec 3 -ErrorAction Stop
    if ($cfg.success -eq $true) {
        Write-Host "   ✅ Config endpoint OK: $configUrl" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Config endpoint responded but success=false: $configUrl" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ⚠️  Config endpoint not reachable: $configUrl" -ForegroundColor Yellow
}

# 检查 LM Studio
Write-Host ""
Write-Host "2️⃣ Checking LM Studio..." -ForegroundColor Yellow
try {
    $models = Invoke-RestMethod -Uri "http://localhost:1234/v1/models" -TimeoutSec 3 -ErrorAction Stop
    $modelCount = $models.data.Count
    Write-Host "   ✅ LM Studio is running with $modelCount model(s)" -ForegroundColor Green
    Write-Host "   Models: $($models.data.id -join ', ')" -ForegroundColor Gray
} catch {
    Write-Host "   ❌ LM Studio not running or no models loaded" -ForegroundColor Red
    Write-Host "   👉 Please start LM Studio and load a model" -ForegroundColor Yellow
    Write-Host "   📖 See SERVICE_SETUP.md for details" -ForegroundColor Gray
}

# 检查 SuryaOCR
Write-Host ""
Write-Host "3️⃣ Checking SuryaOCR..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:5001/health" -TimeoutSec 3 -ErrorAction Stop
    Write-Host "   ✅ SuryaOCR is running on port 5001" -ForegroundColor Green
} catch {
    Write-Host "   ❌ SuryaOCR not running" -ForegroundColor Red
    Write-Host "   👉 To start SuryaOCR:" -ForegroundColor Yellow
    Write-Host "      cd ..\SuryaOCR-main\SuryaOCR-main" -ForegroundColor Gray
    Write-Host "      python server.py --port 5001" -ForegroundColor Gray
    
    $startOCR = Read-Host "   ❓ Do you want to start SuryaOCR now? (y/n)"
    if ($startOCR -eq 'y') {
        if (Test-Path "..\SuryaOCR-main\SuryaOCR-main") {
            Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd ..\SuryaOCR-main\SuryaOCR-main; python server.py --port 5001" -WindowStyle Normal
            Write-Host "   ✅ Started SuryaOCR in new window" -ForegroundColor Green
        } else {
            Write-Host "   ⚠️  SuryaOCR directory not found" -ForegroundColor Yellow
        }
    }
}

# 检查 CosyVoice TTS
Write-Host ""
Write-Host "4️⃣ Checking CosyVoice TTS..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:5003/health" -TimeoutSec 3 -ErrorAction Stop
    Write-Host "   ✅ CosyVoice TTS is running on port 5003" -ForegroundColor Green
} catch {
    Write-Host "   ❌ CosyVoice TTS not running" -ForegroundColor Red
    Write-Host "   👉 To start CosyVoice:" -ForegroundColor Yellow
    Write-Host "      cd <cosyvoice-directory>" -ForegroundColor Gray
    Write-Host "      python cosyvoice_server.py --port 5003" -ForegroundColor Gray
    
    $startTTS = Read-Host "   ❓ Do you want to start CosyVoice TTS now? (y/n)"
    if ($startTTS -eq 'y') {
        Write-Host "   ℹ️  Please manually start CosyVoice (path unknown)" -ForegroundColor Cyan
        Write-Host "   📖 See SERVICE_SETUP.md for detailed instructions" -ForegroundColor Gray
    }
}

# 检查 Whisper ASR
Write-Host ""
Write-Host "5️⃣ Checking Whisper ASR (Optional)..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:5002/health" -TimeoutSec 3 -ErrorAction Stop
    Write-Host "   ✅ Whisper ASR is running on port 5002" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️  Whisper ASR not running (debugging in progress, optional)" -ForegroundColor Yellow
}

# 总结（只汇报真实检查结果）
Write-Host ""
Write-Host "=" -NoNewline; for($i=0;$i -lt 60;$i++){Write-Host "=" -NoNewline}; Write-Host ""
Write-Host "📊 Service Status Summary" -ForegroundColor Cyan
Write-Host "   • FastAPI: OK (port $BackendPort)" -ForegroundColor White
Write-Host "   • LM Studio / OCR / TTS / ASR: see checks above" -ForegroundColor White
Write-Host ""

Write-Host "💡 Next Steps:" -ForegroundColor Cyan
Write-Host "   1. Start dev stack: .\scripts\start.ps1" -ForegroundColor White
Write-Host "   2. Run FastAPI tests: cd backend_fastapi; pytest" -ForegroundColor White
Write-Host "   3. Build v5: cd app\v5; npm run build" -ForegroundColor White
Write-Host ""
