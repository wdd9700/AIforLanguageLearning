# Expert Agent Prompt: 遗留代码清理专家

## 任务目标

完成项目的**最终死代码清理**，删除已迁移的旧代码，确保项目结构整洁，新后端 `backend_fastapi/` 成为唯一活跃代码基。

## 当前状态

- **新后端**: `backend_fastapi/` — FastAPI 架构，已完成 Phase 1~3 迁移和基础设施加固
- **旧后端**: `backend/` — TypeScript/NestJS 架构，代码已迁移至 `backend_fastapi/`，但目录仍存在
- **旧 Python 服务**: `backend/python_services/` — 独立的 ASR/TTS 微服务，端口 8000
- **Git 状态**: 最新提交 `4f0d4da`，已推送至 GitHub

## 需要分析的关键问题

### 1. `backend/python_services/` 的依赖关系

该目录包含：
```
backend/python_services/
├── main.py              # FastAPI 入口，端口 8000
├── requirements.txt
└── routers/
    ├── asr.py           # ASR 路由
    └── tts.py           # TTS 路由
```

**需要确认**:
- 是否有其他代码（前端、测试脚本、配置）显式引用 `localhost:8000` 或 `python_services`
- `backend_fastapi/app/voice_stream.py` 和 `backend_fastapi/app/tts.py` 是否已经完全替代了这些服务
- 如果 `python_services` 仍在被使用，需要制定迁移计划；如果未被使用，可以安全删除

### 2. `backend/` (TypeScript/NestJS) 目录

包含完整的旧后端代码：
```
backend/
├── src/                 # TypeScript 源代码（auth, api, services, models...）
├── python_services/     # 上述 Python 微服务
├── package.json         # Node.js 依赖
└── ...
```

**需要确认**:
- 所有有效代码是否已迁移至 `backend_fastapi/`
- 是否有启动脚本、Docker 配置、CI/CD 仍引用 `backend/`
- 是否可以安全删除或归档

## 执行步骤

### 步骤 1: 依赖分析

1. 搜索整个代码库中对 `python_services`、`localhost:8000`、`backend/` 的引用
2. 检查文件：
   - `scripts/` 目录下的启动/检查脚本
   - `docker-compose*.yml` 文件
   - `.env` 和配置文件
   - 前端代码（如果有）
   - 测试脚本

3. 生成依赖报告：
   - 哪些文件引用了旧代码
   - 引用是必需的还是遗留的
   - 是否需要更新引用指向 `backend_fastapi/`

### 步骤 2: 制定清理计划

根据依赖分析结果，制定清理方案：

**方案 A - 完全删除**（如果无依赖）:
- 删除 `backend/` 整个目录
- 删除相关的 `.zip` 归档文件（已解压的）

**方案 B - 部分保留**（如果部分依赖）:
- 保留仍在使用的部分
- 迁移或删除未使用的部分

**方案 C - 归档**（如果需要保留历史）:
- 将 `backend/` 移动到 `archive/backend-legacy/`
- 添加 `README.md` 说明归档原因

### 步骤 3: 执行清理

1. 备份重要文件（如有必要）
2. 执行删除/归档操作
3. 更新相关配置（如有必要）
4. 验证 `backend_fastapi/` 仍可正常启动和运行测试

### 步骤 4: 验证

1. 运行测试：`pytest tests/ -m "not integration"`
2. 验证 FastAPI 应用可正常启动
3. 确认没有破坏任何功能

## 输出要求

1. **依赖分析报告** (`docs/agent_prompts/phase_5_cleanup/dependency_analysis.md`):
   - 列出所有引用旧代码的文件
   - 评估每个引用的必要性
   - 给出处理建议

2. **清理执行报告** (`docs/agent_prompts/phase_5_cleanup/cleanup_report.md`):
   - 实际执行的清理操作
   - 删除/归档的文件列表
   - 任何配置更新

3. **验证结果**:
   - 测试运行结果
   - 应用启动验证

## 约束条件

- **不要删除** `backend_fastapi/` 中的任何代码
- **不要修改** 核心功能逻辑
- **确保** 清理后 `pytest tests/ -m "not integration"` 仍然全绿
- **保留** 所有文档文件（`docs/` 目录）

## 参考信息

- 新后端入口: `backend_fastapi/app/main.py`
- 新后端测试: `backend_fastapi/tests/`
- 语音/ASR 实现: `backend_fastapi/app/voice_stream.py`, `backend_fastapi/app/tts.py`
- 最新交接文档: `docs/agent_prompts/phase_4_core_features/handoff_*.md`
