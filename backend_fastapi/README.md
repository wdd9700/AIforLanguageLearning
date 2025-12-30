# backend_fastapi

本目录用于承载后端迁移（FastAPI 版本）的实现。

- 里程碑与协议文档：../docs/MIGRATION_MILESTONES_FASTAPI.md

## 开发（Windows / PowerShell）

建议使用 Python 3.11+，但当前工程已支持 Python 3.10+（用于兼容现有 conda 环境）。

1) 创建虚拟环境（示例）
- `python -m venv .venv`
- `./.venv/Scripts/Activate.ps1`

2) 安装依赖
- `python -m pip install -U pip`
- `python -m pip install -e .[dev]`

3) 启动
- `uvicorn app.main:app --reload --port 3007`

如果你遇到 `conda run` 或 `conda activate` 在 PowerShell 中“无输出/失败”等问题，建议直接指定解释器路径启动：
- `./scripts/run_dev.ps1 -PythonExe "C:\\Users\\<you>\\Miniconda3\\envs\\backend_fastapi\\python.exe" -Port 3007`

> 也可以直接使用 venv：`./.venv/Scripts/python.exe`

> 端口后续可对齐现有前端配置。
