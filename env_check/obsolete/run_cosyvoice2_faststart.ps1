# One-click launcher for CosyVoice2 streaming with recommended settings
param(
  [string]$CondaEnvPath = "C:\\Users\\74090\\Miniconda3\\envs\\torchnb311",
  [string]$Langs = "zh",
  [string]$PromptWav = "",
  [string]$OutDir = "",
  [int]$FirstHop = 12,
  [int]$FirstChunks = 1,
  [switch]$RebuildTrt = $false
)

$ErrorActionPreference = 'Stop'

# Recommended environment for best steady-state RTF with low TTFT
$env:COSY_FP16 = '0'              # Internal TRT engine precision (0=FP32)
$env:COSY_AMP_DTYPE = 'bf16'      # PyTorch AMP dtype
$env:COSY_WARMUP = '1'            # Light warmup

# Optional overrides
if ($PromptWav) { $env:COSY_PROMPT_WAV = $PromptWav }
if ($OutDir)    { $env:COSY_OUT_DIR    = $OutDir }

# Optional: rebuild TRT engine for fresh profiles (costly, may improve first-run TTFT)
if ($RebuildTrt) { $env:COSY_REBUILD_TRT = '1' } else { Remove-Item Env:COSY_REBUILD_TRT -ErrorAction SilentlyContinue }

# Delegate to the main runner with recommended knobs
$script = Join-Path $PSScriptRoot 'run_iobind_windows.ps1'
if (-not (Test-Path $script)) { throw "Cannot find runner: $script" }

& $script -CondaEnvPath $CondaEnvPath -Langs $Langs -TryTRT -TrtFp16:$false -TokenHop 32 -FirstHop $FirstHop -FirstChunks $FirstChunks -LoadTrtEstimator
if ($LASTEXITCODE -ne 0) { throw "Faststart failed with exit code $LASTEXITCODE" }
