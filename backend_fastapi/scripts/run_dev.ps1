param(
  [string]$PythonExe = "python",
  [int]$Port = 3007
)

$ErrorActionPreference = "Stop"

# 说明：
# - Windows 上若 conda 激活/conda run 有输出异常，可直接指定解释器路径：
#   ./scripts/run_dev.ps1 -PythonExe "C:\Users\...\Miniconda3\envs\backend_fastapi\python.exe"

& $PythonExe -m uvicorn app.main:app --reload --port $Port
