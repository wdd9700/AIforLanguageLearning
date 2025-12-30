# 快速启动所有服务

Write-Host "🚀 AI Language Learning - Service Launcher" -ForegroundColor Cyan
Write-Host "=" -NoNewline; for($i=0;$i -lt 60;$i++){Write-Host "=" -NoNewline}; Write-Host ""
Write-Host ""

# 检查后端是否运行
Write-Host "1️⃣ Checking Backend Server..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:3000/api/system/health" -TimeoutSec 3 -ErrorAction Stop
    Write-Host "   ✅ Backend is running on port 3000" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️  Backend not running. Starting..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd ..\backend; npm run dev" -WindowStyle Normal
    Write-Host "   ⏳ Waiting for backend to start..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
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

# 总结
Write-Host ""
Write-Host "=" -NoNewline; for($i=0;$i -lt 60;$i++){Write-Host "=" -NoNewline}; Write-Host ""
Write-Host "📊 Service Status Summary" -ForegroundColor Cyan
Write-Host ""

# 运行详细检查
Set-Location ..\backend
Write-Host "Running detailed service check..." -ForegroundColor Gray
npm run check

Write-Host ""
Write-Host "💡 Next Steps:" -ForegroundColor Cyan
Write-Host "   1. Ensure all required services are running (✅)" -ForegroundColor White
Write-Host "   2. Run tests: npm run test:services" -ForegroundColor White
Write-Host "   3. Run API tests: npm run test:endpoints" -ForegroundColor White
Write-Host "   4. View logs: backend/logs/app.log" -ForegroundColor White
Write-Host ""
Write-Host "📖 For detailed setup instructions, see ../docs/backend/SERVICE_SETUP.md" -ForegroundColor Gray
Write-Host ""
