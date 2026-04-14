# 依赖分析报告 - Phase 5 死代码清理

**生成日期**: 2026年4月14日  
**分析范围**: `backend/` (旧 TypeScript/NestJS 后端) 和 `backend/python_services/` (旧 Python 微服务)  
**分析目标**: 确认旧代码是否仍被项目其他部分引用，评估安全删除的可行性

---

## 1. 执行摘要

| 项目 | 状态 | 结论 |
|------|------|------|
| `backend/python_services/` | 🔴 **无活跃引用** | 可安全删除 |
| `backend/` (TypeScript/NestJS) | 🟡 **仅文档/测试引用** | 可安全删除（需更新部分测试文件） |
| `localhost:8000` 引用 | 🟢 **已迁移处理** | 前端配置已自动重定向到 8012 |

---

## 2. `backend/python_services/` 依赖分析

### 2.1 目录内容

```
backend/python_services/
├── main.py              # FastAPI 入口，端口 8000
├── requirements.txt     # 独立依赖
└── routers/
    ├── asr.py           # ASR 路由
    └── tts.py           # TTS 路由
```

### 2.2 引用搜索结果

| 引用位置 | 引用内容 | 评估 |
|----------|----------|------|
| `backend/scripts/diagnose_services.py:102` | `def check_python_services()` | 🔴 **旧诊断脚本本身属于 backend/，将被删除** |
| `backend/scripts/diagnose_services.py:162` | `results['Python 服务'] = check_python_services()` | 🔴 **同上** |
| `docs/agent_prompts/phase_5_cleanup/expert_05_legacy_cleanup.md` | 任务描述文档 | 🟢 文档引用，非代码依赖 |

### 2.3 替代方案确认

新后端 `backend_fastapi/` 已完全替代 `python_services` 的功能：

| 功能 | 旧位置 | 新位置 | 状态 |
|------|--------|--------|------|
| ASR | `backend/python_services/routers/asr.py` | `backend_fastapi/app/voice_stream.py` | ✅ 已迁移 |
| TTS | `backend/python_services/routers/tts.py` | `backend_fastapi/app/tts.py` | ✅ 已迁移 |
| WebSocket 语音 | 无 | `backend_fastapi/app/websocket_voice.py` | ✅ 新功能 |

### 2.4 端口 8000 引用分析

搜索 `localhost:8000` 发现以下引用：

| 文件 | 引用内容 | 评估 |
|------|----------|------|
| `app/v5/src/services/config.ts:83` | `url.replace('http://localhost:8000', 'http://localhost:8012')` | 🟢 **自动重定向逻辑** |
| `app/v5/src/services/api.ts:29` | `.replace('http://localhost:8000', 'http://localhost:8012')` | 🟢 **自动重定向逻辑** |
| `app/v5/src/stores/voice.ts:69` | 注释：避免连接到前端 dev server | 🟢 **注释说明** |
| `app/v5/electron/main/managers/ipc-manager.ts:18` | `url.replace('http://localhost:8000', 'http://localhost:8012')` | 🟢 **自动重定向逻辑** |
| `backend_fastapi/app/routers/system.py:56,67` | `value.replace("localhost:8000", "localhost:8012")` | 🟢 **后端配置自动重定向** |

**结论**: 所有 `localhost:8000` 引用都是**自动重定向逻辑**，用于将旧端口配置迁移到新端口 8012。这证明 `python_services` (端口 8000) 已不再被直接使用。

---

## 3. `backend/` (TypeScript/NestJS) 依赖分析

### 3.1 目录内容概览

```
backend/
├── src/                 # TypeScript 源代码 (~10,243 LOC)
├── python_services/     # Python 微服务（上述已分析）
├── scripts/             # 诊断和测试脚本
├── tests/               # TypeScript 测试
├── docs/                # 文档（部分需要保留）
├── package.json         # Node.js 依赖
├── ecosystem.config.js  # PM2 配置
└── ...
```

### 3.2 引用搜索结果

#### 3.2.1 根级别配置文件

| 文件 | 引用内容 | 评估 |
|------|----------|------|
| `.gitignore:77-79` | `backend/logs/`, `backend/temp/`, `backend/data/*.sqlite*` | 🟡 **删除 backend/ 后这些规则将失效，但不影响功能** |
| `.gitattributes:1` | `backend/tests/*.wav filter=lfs` | 🟡 **删除 backend/ 后失效** |
| `package.json` | 仅 devDependencies，无 backend/ 脚本 | 🟢 **根级别 package.json 不依赖 backend/** |

#### 3.2.2 脚本文件

| 文件 | 引用内容 | 评估 |
|------|----------|------|
| `scripts/start-services.ps1:5` | 注释：旧的 Node 后端属于 legacy | 🟢 **仅注释说明** |

#### 3.2.3 测试文件

| 文件 | 引用内容 | 评估 |
|------|----------|------|
| `tests/test-integration.ts:6` | `import { ServiceManager } from '../backend/src/managers/service-manager'` | 🔴 **需要删除或更新** |
| `tests/test-quick.ts:5` | `import { ServiceManager } from '../backend/src/managers/service-manager'` | 🔴 **需要删除或更新** |
| `tests/test-endpoints.ts:195,280` | 引用 `backend/test-image.png`, `backend/test-audio.wav` | 🔴 **需要删除或更新** |
| `tests/test-services.ts:148,269` | 引用 `backend/test-image.png`, `backend/test-audio.wav` | 🔴 **需要删除或更新** |
| `tests/test-service-refresh.ps1:110` | 引用 `backend/src/api/routes/system.ts` | 🔴 **需要删除或更新** |
| `tests/test-ocr.ts:5,8` | 引用 `backend/scripts/test_all_services.py` | 🟡 **信息性引用** |

#### 3.2.4 文档文件

| 文件 | 引用内容 | 评估 |
|------|----------|------|
| `docs/development_guide/SSD_BMAD_Architecture_Transformation_Plan.md` | 架构转型文档，引用 backend/ 作为旧架构 | 🟢 **历史文档，保留** |
| `docs/agent_prompts/phase_1_dead_code_cleanup/*.md` | Phase 1 文档，引用 backend/src/ | 🟢 **历史文档，保留** |

#### 3.2.5 NewBasicMoudules（其他成员交付物）

| 文件 | 引用内容 | 评估 |
|------|----------|------|
| `NewBasicMoudules/*/code/**` | 多处引用 `localhost:8000` | 🟢 **独立交付物，不影响主项目** |
| `NewBasicMoudules/*/docs/**` | API 文档引用 `localhost:8000` | 🟢 **独立交付物文档** |

### 3.3 启动脚本和 CI/CD 检查

| 检查项 | 状态 | 说明 |
|--------|------|------|
| `ecosystem.config.js` | 🟡 存在 | PM2 配置，使用 `backend/dist/index.js`，删除 backend/ 后失效 |
| `docker-compose*.yml` | 🟢 无引用 | 所有 docker-compose 文件都在 `backend_fastapi/`，使用新后端 |
| `.github/workflows/` | 🟢 无引用 | 检查确认无 CI/CD 引用 backend/ |

### 3.4 前端代码检查

| 检查项 | 状态 | 说明 |
|--------|------|------|
| `app/v5/src/` | 🟢 无直接引用 | 前端代码通过配置文件连接后端，无硬编码 backend/ 路径 |
| `app/v5/electron/` | 🟢 无直接引用 | Electron 主进程通过 IPC 获取配置 |

---

## 4. 依赖关系图

```
┌─────────────────────────────────────────────────────────────────┐
│                        项目结构                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌──────────────────┐                   │
│  │   app/v5/       │◄──►│  backend_fastapi/ │  ◄── 活跃后端      │
│  │   (前端)         │    │  (FastAPI 8012)   │                   │
│  └─────────────────┘    └──────────────────┘                   │
│           ▲                        ▲                           │
│           │                        │                           │
│           │    自动重定向 8000→8012  │                           │
│           │    (config.ts, system.py)│                           │
│           │                        │                           │
│  ┌────────┴────────┐              │                           │
│  │  backend/       │              │                           │
│  │  (TypeScript)   │──────────────┘                           │
│  │  ─────────────  │    已迁移                                │
│  │  python_services│                                          │
│  │  (端口 8000)    │  ◄── 死代码，待删除                       │
│  └─────────────────┘                                          │
│                                                                 │
│  ┌─────────────────┐                                           │
│  │  tests/         │  ◄── 部分测试引用 backend/，需清理         │
│  │  (根级别)        │                                           │
│  └─────────────────┘                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. 处理建议

### 5.1 `backend/python_services/` — 完全删除

- **理由**: 无任何活跃代码引用，功能已完全迁移到 `backend_fastapi/`
- **操作**: 直接删除整个目录
- **风险**: 无

### 5.2 `backend/` (TypeScript/NestJS) — 完全删除

- **理由**: 
  - 代码已迁移至 `backend_fastapi/`
  - 无活跃运行时依赖
  - 前端和配置已自动重定向到新后端
- **操作**: 直接删除整个目录
- **风险**: 低（需同步删除根级别 tests/ 中引用 backend/ 的测试文件）

### 5.3 根级别 `tests/` — 选择性删除

以下测试文件引用 `backend/`，需要删除或更新：

| 文件 | 操作 | 理由 |
|------|------|------|
| `tests/test-integration.ts` | 🔴 删除 | 引用 `backend/src/managers/service-manager` |
| `tests/test-quick.ts` | 🔴 删除 | 引用 `backend/src/managers/service-manager` |
| `tests/test-endpoints.ts` | 🔴 删除 | 引用 `backend/test-image.png` 等 |
| `tests/test-services.ts` | 🔴 删除 | 引用 `backend/test-image.png` 等 |
| `tests/test-service-refresh.ps1` | 🔴 删除 | 引用 `backend/src/api/routes/system.ts` |
| `tests/test-ocr.ts` | 🟡 保留 | 仅信息性引用，可修改为指向新后端脚本 |

### 5.4 配置文件清理

| 文件 | 操作 | 说明 |
|------|------|------|
| `.gitignore` | 🟡 可选 | 删除 backend/ 相关规则（非必须） |
| `.gitattributes` | 🟡 可选 | 删除 backend/ 相关规则（非必须） |

---

## 6. 清理计划

### 方案 A: 完全删除（推荐）

1. 删除 `backend/` 整个目录（包含 `python_services/`）
2. 删除根级别 `tests/` 中引用 backend/ 的测试文件
3. 可选：清理 `.gitignore` 和 `.gitattributes`

### 方案 B: 归档保留

1. 将 `backend/` 移动到 `archive/backend-legacy/`
2. 保留根级别 `tests/` 但标记为废弃

**推荐方案 A**，因为：
- Git 历史已保留旧代码
- 项目明确迁移到 FastAPI
- 归档会增加维护负担

---

## 7. 验证清单

清理后需要验证：

- [ ] `backend_fastapi/` 仍可正常启动
- [ ] `pytest tests/ -m "not integration"` 全绿
- [ ] 前端 `app/v5/` 可正常连接后端
- [ ] 无运行时错误

---

## 附录：引用详细列表

### A.1 `python_services` 相关引用

```
docs/agent_prompts/phase_5_cleanup/expert_05_legacy_cleanup.md (任务文档)
backend/scripts/diagnose_services.py:102,162 (将被删除)
```

### A.2 `backend/` 相关引用

```
.gitignore:77-79
.gitattributes:1
docs/development_guide/SSD_BMAD_Architecture_Transformation_Plan.md:81,129,413
docs/agent_prompts/phase_1_dead_code_cleanup/*.md (历史文档)
tests/test-integration.ts:6
tests/test-quick.ts:5,15,61
tests/test-endpoints.ts:195,280
tests/test-services.ts:148,269
tests/test-service-refresh.ps1:110
tests/test-ocr.ts:5,8
scripts/start-services.ps1:5 (注释)
```

### A.3 `localhost:8000` 引用（自动重定向）

```
app/v5/src/services/config.ts:83,91
app/v5/src/services/api.ts:29
app/v5/src/stores/voice.ts:69 (注释)
app/v5/electron/main/managers/ipc-manager.ts:18,25
backend_fastapi/app/routers/system.py:56,67
```
