# 测试 CosyVoice2 GPU 集成
# 使用项目优化的环境和配置

$ErrorActionPreference = 'Stop'

Write-Host "🔊 Testing CosyVoice2 GPU TTS Integration" -ForegroundColor Cyan
Write-Host ""

# 项目路径
$ProjectRoot = "E:\projects\AiforForiegnLanguageLearning"
$PythonExe = "C:\Users\74090\Miniconda3\envs\torchnb311\python.exe"
$TestText = "收到好友从远方寄来的生日礼物，那份意外的惊喜与深深的祝福让我心中充满了甜蜜的快乐。"
$PromptWav = Join-Path $ProjectRoot "testresources\TTSpromptAudio.wav"
$OutputDir = Join-Path $ProjectRoot "backend\temp"

# 确保输出目录存在
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

# 设置环境变量（项目推荐配置）
$env:COSY_TOKEN_HOP = '32'
$env:COSY_WARMUP = '1'
$env:COSY_AMP_DTYPE = 'bf16'
$env:COSY_FP16 = '0'
$env:COSY_PROMPT_WAV = $PromptWav

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Python: $PythonExe"
Write-Host "  Text: $TestText"
Write-Host "  Prompt: $PromptWav"
Write-Host "  Token Hop: $env:COSY_TOKEN_HOP"
Write-Host "  AMP dtype: $env:COSY_AMP_DTYPE"
Write-Host ""

# 运行项目现有的测试脚本
Push-Location $ProjectRoot
try {
    Write-Host "Running env_check/run_cosyvoice2_zero_shot.py..." -ForegroundColor Green
    
    & $PythonExe -m env_check.run_cosyvoice2_zero_shot `
        --text $TestText `
        --prompt_wav $PromptWav `
        --use_fp16 1 `
        --use_flow_cache 1
    
    if ($LASTEXITCODE -ne 0) {
        throw "CosyVoice2 test failed with exit code $LASTEXITCODE"
    }
    
    Write-Host ""
    Write-Host "✅ TTS test completed!" -ForegroundColor Green
    Write-Host ""
    
    # 检查生成的文件
    $GeneratedFiles = Get-ChildItem -Path (Join-Path $ProjectRoot "env_check") -Filter "zero_shot_*.wav" -ErrorAction SilentlyContinue
    if ($GeneratedFiles.Count -gt 0) {
        Write-Host "Generated files:" -ForegroundColor Cyan
        $GeneratedFiles | ForEach-Object {
            Write-Host "  $($_.Name) - $([Math]::Round($_.Length / 1KB, 2)) KB" -ForegroundColor White
        }
    }
    
} finally {
    Pop-Location
}
