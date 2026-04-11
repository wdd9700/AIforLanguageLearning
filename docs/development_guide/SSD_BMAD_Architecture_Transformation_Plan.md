# AI外语学习系统 - SSD与BMAD驱动的架构转型计划

**文档版本**: v1.0  
**创建日期**: 2026年4月11日  
**指导原则**: SSD (Specification-Driven Development) + BMAD (Business Model-Driven Architecture Design)

---

## 一、核心理念阐述

### 1.1 SSD（规范驱动开发）原则

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SSD 核心循环                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   规范定义 ──────► 代码实现 ──────► 自动验证 ──────► 规范更新              │
│       ▲                                              │                      │
│       └──────────────────────────────────────────────┘                      │
│                                                                             │
│   原则：                                                                      │
│   1. 先写规范，后写代码                                                       │
│   2. 规范即契约，代码必须100%符合规范                                          │
│   3. 自动化验证规范符合性                                                      │
│   4. 规范变更必须通过评审流程                                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 BMAD（业务模型驱动架构设计）原则

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       BMAD 四层架构                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Layer 4: 业务模型层 (Business Model)                                │   │
│  │  • 领域实体 (Domain Entities)                                        │   │
│  │  • 业务流程 (Business Processes)                                     │   │
│  │  • 业务规则 (Business Rules)                                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Layer 3: 应用服务层 (Application Services)                          │   │
│  │  • 用例实现 (Use Case Implementation)                                │   │
│  │  • 工作流编排 (Workflow Orchestration)                               │   │
│  │  • 事务边界 (Transaction Boundaries)                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Layer 2: 基础设施层 (Infrastructure)                                │   │
│  │  • 数据持久化 (Data Persistence)                                     │   │
│  │  • 外部服务集成 (External Service Integration)                       │   │
│  │  • 消息队列 (Message Queue)                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Layer 1: 接口适配层 (Interface Adapters)                            │   │
│  │  • REST API / WebSocket                                              │   │
│  │  • 数据转换 (DTOs)                                                   │   │
│  │  • 认证授权 (Auth)                                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  原则：业务模型独立于技术实现，技术变更不应影响业务逻辑                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、当前架构现状分析

### 2.1 现有代码结构诊断

```
backend_fastapi/app/                    backend/src/
├── context_store.py      ◄─────┐       ├── api/              ◄─────┐
├── db.py                       │       ├── auth/                     │
├── llm.py                      │       ├── controllers/              │
├── logging.py                  │       ├── database/                 │
├── main.py                     │       ├── infra/                    │
├── models.py                   │       ├── managers/                 │
├── model_router.py             │       ├── middleware/               │
├── ocr.py                      │       ├── models/                   │
├── prompts/                    │       ├── orchestrator/             │
├── prompts.py                  │       ├── security/                 │
├── retry_utils.py              │       ├── services/                 │
├── routers/                    │       ├── shared/                   │
├── runtime_config.py           │       ├── softbus/                  │
├── settings.py                 │       └── utils/                    │
├── token_utils.py              │                                     │
├── tts.py                      │       问题：                         │
├── voice_stream.py             │       1. 双轨并行，重复实现          │
└── __init__.py                 │       2. 职责边界不清晰              │
                                │       3. 缺乏统一规范                │
        问题：                   │                                     │
        1. 模块间耦合度高        └─────────────────────────────────────┘
        2. 缺乏清晰的业务模型抽象
        3. 测试覆盖不足
```

### 2.2 新模块交付物映射

```
NewBasicMoudules/
├── database_search_layer_deliverable/     ◄── 成员1 (7.6/10)
│   └── 问题：测试文件缺失，PostgreSQL版本不一致
│
├── delivery_sprint3_4_knowledge_graph/    ◄── 成员3 (8.35/10) ✅
│   └── 状态：优秀，可集成
│
├── part_d_security/                       ◄── 成员4 (6.05/10)
│   └── 问题：未与主项目集成，审计日志缺失
│
└── team_onboarding/                       ◄── 成员2 (4.65/10)
    ├── infrastructure/                    ◄── 问题：目录为空！
    └── mq_and_rtc/                        ◄── 问题：仅代码，无部署配置
```

---

## 二点五、迁移价值深度评估（基于实际代码分析）

> 本节基于对 `backend/`（Node.js/TypeScript）和 `backend_fastapi/`（Python/FastAPI）两套代码的深入分析，评估迁移到新模块的技术价值与业务价值。

---

### 2.3 旧 backend 技术栈与架构问题

#### 2.3.1 技术栈概览
| 层级 | 实现 | 代码量 |
|------|------|--------|
| API Routes (`Express Router`) | 7 个文件 | 499 LOC |
| Controllers | 7 个文件 | 1,731 LOC |
| Services | 6 个文件 | 1,473 LOC |
| Managers | 7 个文件 | 1,088 LOC |
| Database / Orchestrator / Infra | 其余 | ~5,475 LOC |
| **合计** | **64 个文件** | **10,266 LOC** |
| 测试 | 8 个文件 | 632 LOC |

#### 2.3.2 核心架构问题

**A. 跨语言桥接层过重**
- `ASRService`、`TTSService`、`OCRService` 均通过 `child_process.spawn` 调用 Python 脚本
- 需要手动管理子进程生命周期、标准输入输出协议、JSON 行解析、超时和错误恢复
- 例如 `tts.service.ts` 中，TTS 进程通过 `stdio: ['pipe', 'pipe', 'pipe']` 进行通信，存在明显的跨语言序列化开销

**B. 自研基础设施代码占比过高**
- 自定义 `BaseService` + `EventEmitter` 状态机
- 自定义 `ServiceManager` 负责服务激活和健康检查
- 自定义 `Orchestrator` + `MessageProcessor` 实现消息路由和流水线
- 手动编写 SQLite migration（`db.ts` 中硬编码了 10+ 张表的 `CREATE TABLE IF NOT EXISTS`）
- 这些功能在 Python 生态中均有成熟替代（FastAPI 依赖注入、SQLModel/Alembic、Celery/RQ 等）

**C. 数据库层缺乏 ORM**
- 所有 SQL 均为手写字符串，类型安全依赖注释
- 无连接池管理，无 schema 版本控制
- 查询逻辑散落在 Controllers 和 Services 中

**D. WebSocket 实现复杂度高**
- 手动处理 `httpServer.on('upgrade')`，区分 `/stream` 和 `/logs` 路径
- 没有统一的事件协议框架，语音流、日志流、业务流各自维护状态

---

### 2.4 backend_fastapi 技术栈优势

#### 2.4.1 技术栈概览
| 层级 | 实现 | 代码量 |
|------|------|--------|
| Routers / Endpoints | 9 个文件 | ~1,400 LOC |
| Core (LLM/TTS/OCR/DB/Models) | 12 个文件 | ~3,200 LOC |
| Voice Stream / WS | 2 个文件 | ~600 LOC |
| **合计** | **25 个文件** | **5,236 LOC** |
| 测试 | 22 个文件 | **1,467 LOC** |

#### 2.4.2 核心优势

**A. 原生 AI 生态集成**
- `llm.py` 直接通过 `httpx.AsyncClient` 调用 OpenAI 兼容接口，支持异步流式响应
- `voice_stream.py` 原生集成 `faster-whisper` 和 `webrtcvad`，无需跨进程通信
- `tts.py` 原生集成 `TTS.api` (XTTS v2)，支持 GPU 自动检测
- `ocr.py` 原生集成 `PaddleOCR`，并带 `rapidocr_onnxruntime` 兜底

**B. 现代化数据层**
- `SQLModel` + `SQLAlchemy 2.0` 提供类型安全的 ORM
- `Alembic` 已列入依赖，支持数据库版本迁移
- `db.py` 仅 50 行即完成引擎创建、连接池管理和会话依赖注入

**C. 内置兼容层降低前端迁移成本**
- `compat_legacy.py` 已实现对旧 API 的兼容：
  - `/api/query/vocabulary`
  - `/api/query/ocr`
  - `/api/essay/correct`
  - `/api/learning/stats`
  - `/api/learning/analyze`
- 这意味着**前端可以零改动切换到 FastAPI 后端**

**D. 更健壮的 WebSocket 设计**
- 统一事件协议（`seq`, `conversation_id`, `request_id`, `payload`）
- 支持断线重连和 `last_seq` 恢复
- 内置 VAD 自动判停，无需客户端发送 `AUDIO_END`

**E. 测试覆盖度更高**
- FastAPI 测试代码（1,467 LOC）已是旧后端（632 LOC）的 **2.3 倍**
- 使用 `pytest-asyncio`，天然适合测试异步 WebSocket 和流式接口

---

### 2.5 迁移成本与收益量化评估

#### 2.5.1 代码量对比
| 项目 | 旧 backend | backend_fastapi | 状态 |
|------|-----------|-----------------|------|
| 业务代码 LOC | 10,266 | 5,236 | 已重写 ~51% |
| 测试代码 LOC | 632 | 1,467 | 已覆盖更多 |
| 文件数 | 64 | 25 | 精简 61% |

#### 2.5.2 功能覆盖度分析

**FastAPI 后端已实现**：
- ✅ 词汇查询（含 LLM 生成兜底）
- ✅ OCR（PaddleOCR + rapidocr 兜底）
- ✅ 作文批改（结构化评分）
- ✅ 学习统计 / 分析
- ✅ 语音对话 WebSocket（含 VAD、断线恢复、TTS）
- ✅ 旧 API 兼容层
- ✅ 认证路由（最小可用）
- ✅ 系统状态/模型路由

**尚未迁移或待确认的功能**：
- 学习路径 (`learning_paths`) 和学生档案的完整 CRUD
- 生词本 SRS 间隔重复算法的完整实现
- LLM 微调数据收集表 (`llm_finetune_data`)
- 软总线 (ZeroMQ) 和 mDNS 服务发现
- 多用户并发下的数据库隔离策略
- Admin 后台、系统监控、备份恢复

#### 2.5.3 量化迁移工时估算

| 任务 | 预估工时 |
|------|---------|
| 学生档案 / 学习路径 CRUD | 2~3 天 |
| 生词本 SRS 算法完整实现 | 2~3 天 |
| 系统管理 / Admin 接口补齐 | 1~2 天 |
| 端到端集成测试 + Bug 修复 | 3~5 天 |
| 部署脚本 / 文档更新 | 1~2 天 |
| **总计** | **9~15 天（1.5~3 人周）** |

> 若仅追求"功能等价"（利用现有兼容层），工时可能压缩至 **5~8 天**。

#### 2.5.4 性能提升预估
| 维度 | 旧 backend | backend_fastapi | 预估提升 |
|------|-----------|-----------------|----------|
| **LLM 调用延迟** | Axios 同步调用，无原生流式 | `httpx.AsyncClient` + `async for` 流式 | 首 token 延迟降低 **30~50%** |
| **ASR 处理延迟** | Node.js `spawn` + 文件交换 | 原生 `faster-whisper` + 内存缓冲 | 单次识别延迟降低 **40~60%** |
| **TTS 启动时间** | 子进程冷启动 2s+ | 可选 XTTS 常驻内存 / silence 兜底 | 首次合成从 **2s 降至 <200ms** |
| **并发连接** | Express 单线程 + 回调 | Uvicorn 异步多 worker | 同硬件并发能力提升 **2~5 倍** |
| **内存占用** | Node.js + Python 子进程双份 | 单 Python 进程 | 预计减少 **20~40%** |

---

### 2.6 新模块 vs 旧代码 业务价值对比

| 成员 | 模块 | 功能增量 | 质量提升 | 集成成本 | ROI | 建议优先级 |
|------|------|---------|---------|---------|-----|-----------|
| 成员4 | 安全认证 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐☆ | 中 | ⭐⭐⭐⭐⭐ | **P0 - 立即集成** |
| 成员5 | 模型路由+上下文 | ⭐⭐⭐⭐☆ | ⭐⭐⭐⭐☆ | 低 | ⭐⭐⭐⭐⭐ | **P0 - 已集成，持续优化** |
| 成员1 | 数据库+ES+Redis | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐☆ | 中高 | ⭐⭐⭐⭐☆ | **P1 - 分阶段引入** |
| 成员3 | 知识图谱+推荐 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐☆☆ | 中高 | ⭐⭐⭐☆☆ | **P2 - 先图谱后推荐** |

#### 详细分析

**成员1（数据库+ES+Redis）**：
- 旧代码：仅 SQLite 手写 SQL，无 ES、无 Redis、无 ORM
- 新模块：PostgreSQL + SQLAlchemy ORM + ES 全文搜索 + Redis 缓存/分布式锁
- 价值：从单文件 SQLite 跃迁到企业级数据基础设施，词汇搜索体验显著提升
- 建议：**分阶段引入**（先 PG 替换 SQLite → 再引入 Redis → 最后 ES）

**成员3（知识图谱+推荐）**：
- 旧代码：完全空白，仅有简单的 `SynonymRelation` 关系表
- 新模块：Neo4j 图数据库 + LightFM/FAISS 混合推荐 + A* 学习路径
- 价值：纯增量，但推荐系统需要用户行为数据积累才能生效
- 建议：**先落地词汇关系网络，推荐系统延后**

**成员5（模型路由+上下文）**：
- 旧代码：`llm.py` 直接调用 API，无策略路由，无上下文管理
- 新模块：场景化路由 + 故障切换 + 滑动窗口上下文 + Token 压缩
- 价值：已经是主项目运行时代码，无需额外迁移
- 建议：**持续优化端点配置动态化**

**成员4（安全认证）**：
- 旧代码：硬编码 `admin/admin`，无 JWT、无权限控制
- 新模块：完整的 RBAC + JWT + HttpOnly Cookie + CSRF + 速率限制
- 价值：从"演示级"到"生产级"的质变，直接解锁"可上线"状态
- 建议：**最紧迫，立即集成到主项目**

---

### 2.7 迁移策略评估与推荐

#### 2.7.1 策略A：保留双轨运行
| 维度 | 评分 | 说明 |
|------|------|------|
| 开发成本 | 高 | 网关层、认证同步、数据同步均需大量胶水代码 |
| 运维成本 | **极高** | 两个运行时、两套日志、两套部署脚本 |
| 数据一致性风险 | **极高** | 双库并行，无天然同步机制 |
| 推荐度 | ⭐ | **不推荐** |

#### 2.7.2 策略B：部分迁移
| 维度 | 评分 | 说明 |
|------|------|------|
| 开发成本 | 中 | 主要是网关/认证适配 + 跨服务调用 |
| 运维成本 | 中 | 两个服务，但旧后端进入维护模式 |
| 数据一致性风险 | 中 | 需要定义清晰的跨服务数据写入协议 |
| 推荐度 | ⭐⭐⭐ | **可作为 3~6 个月过渡方案** |

#### 2.7.3 策略C：全面迁移
| 维度 | 评分 | 说明 |
|------|------|------|
| 开发成本 | 高（一次性） | 2~3 个月集中开发 |
| 运维成本 | **极低** | 最终只剩一个 Python 运行时 |
| 数据一致性风险 | 低 | 单库单 Schema，无同步问题 |
| 技术债务 | **极低** | 架构统一，长期收益最大 |
| 推荐度 | ⭐⭐⭐⭐⭐ | **长期最优解** |

#### 2.7.4 推荐方案

**策略C（全面迁移），但采用"网关掩护下的分阶段推进"**

即：**目标是一次性全面迁移到 `backend_fastapi`，但执行路径上先通过 Nginx/API Gateway 做流量调度，按模块灰度切换，降低阻断风险。**

**核心理由**：
1. `backend_fastapi` 已承载最具技术壁垒的核心能力（语音对话 WS、ASR→LLM→TTS pipeline）
2. 旧后端"高价值保留功能"（认证、SRS、Admin）迁移成本可控，约 1.5~3 人周
3. 双轨/部分迁移的数据一致性风险不可接受（学习记录、生词本不能分裂）
4. 团队 AI 工程能力集中在 Python，保留 Node 后端长期不经济
5. 不迁移的代价：双轨维护 6 个月额外成本约 3~5 人周，已超过一次性迁移投入

**执行时间线**：
```
Phase 1（第1-3周）：Schema 与认证
  └─ 重建 users, students, vocabulary, learning_records 等 SQLModel
  └─ 实现 JWT 注册/登录/刷新，数据迁移脚本
  └─ 网关层：/api/auth/* /api/learning/* 切到 FastAPI

Phase 2（第4-6周）：Admin & System
  └─ 迁移备份、日志、系统监控、Prompt 管理、用户管理
  └─ 实现 /logs WebSocket
  └─ 网关层：/api/admin/* /api/system/* 切到 FastAPI

Phase 3（第7-8周）：软总线与灰度
  └─ 评估 mDNS/软总线是否仍需保留
  └─ 全量 E2E 测试，逐步切生产流量
```

**风险兜底**：
- 保留旧 backend 的部署配置 3 个月，网关层随时可 5 分钟回切
- 迁移期间禁止在旧 backend 上开发新功能
- 迁移前对旧 `.db` 文件和 `.env` 做快照

---

## 三、转型工作分解（基于SSD+BMAD）

### 3.1 阶段一：规范制定与死代码识别（Week 1）

#### 3.1.1 业务模型规范定义（BMAD Layer 4）

```yaml
# 规范文件: specs/domain_models.yml
# 遵循SSD原则：先定义规范，后实现代码

domain_models:
  Vocabulary:
    description: 词汇领域实体
    attributes:
      - id: UUID
      - term: str
      - phonetic: str
      - difficulty: Enum[BEGINNER, INTERMEDIATE, ADVANCED]
      - tags: List[Tag]
    behaviors:
      - search(query: str) -> List[Vocabulary]
      - get_synonyms() -> List[Vocabulary]
      - get_cognates() -> List[Vocabulary]
    invariants:
      - term must be unique
      - difficulty must be valid enum value

  LearningSession:
    description: 学习会话
    attributes:
      - id: UUID
      - user_id: UUID
      - session_type: Enum[CHAT, ESSAY, VOCAB]
      - context: ConversationContext
    behaviors:
      - start() -> Session
      - resume(session_id: UUID) -> Session
      - end() -> Summary
```

#### 3.1.2 死代码识别清单

| 位置 | 代码/文件 | 状态 | 处理建议 |
|------|-----------|------|----------|
| `backend/src/` | 整个目录 | 🔴 待清理 | 评估后迁移或删除 |
| `backend_fastapi/app/routers/auth.py` | admin/admin模拟登录 | 🔴 死代码 | 替换为成员4的安全模块 |
| `backend_fastapi/app/db.py` | 旧数据库配置 | 🟡 待评估 | 对比成员1的实现 |
| `backend_fastapi/app/llm.py` | 旧LLM调用 | 🟡 待评估 | 对比成员5的路由器 |
| `backend_fastapi/app/voice_stream.py` | 旧语音流 | 🟡 待评估 | 保留或重构 |

### 3.2 阶段二：旧模块清理与架构融合（Week 2-3）

#### 3.2.1 清理策略（SSD规范先行）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     模块清理决策矩阵                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  评估维度：                                                                  │
│  ┌─────────────────┬─────────────────┬─────────────────┐                   │
│  │   功能完整性     │   代码质量       │   集成成本       │                   │
│  │   (0-10分)      │   (0-10分)      │   (0-10分)      │                   │
│  └────────┬────────┴────────┬────────┴────────┬────────┘                   │
│           │                 │                 │                            │
│           ▼                 ▼                 ▼                            │
│  决策规则：                                                                  │
│  • 总分 > 20: 保留并集成                                                    │
│  • 15 < 总分 ≤ 20: 重构后集成                                               │
│  • 总分 ≤ 15: 废弃，重新实现                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 3.2.2 新架构目录结构（BMAD分层）

```
backend_fastapi/
├── app/
│   ├── domain/                    # BMAD Layer 4: 业务模型层
│   │   ├── __init__.py
│   │   ├── models.py              # 核心领域实体
│   │   ├── vocabulary.py          # 词汇领域
│   │   ├── conversation.py        # 对话领域
│   │   ├── essay.py               # 作文领域
│   │   └── user.py                # 用户领域
│   │
│   ├── application/               # BMAD Layer 3: 应用服务层
│   │   ├── __init__.py
│   │   ├── services/
│   │   │   ├── vocabulary_service.py
│   │   │   ├── conversation_service.py
│   │   │   ├── essay_service.py
│   │   │   └── recommendation_service.py
│   │   ├── use_cases/
│   │   │   ├── lookup_word.py
│   │   │   ├── grade_essay.py
│   │   │   └── chat_dialogue.py
│   │   └── workflows/
│   │       └── learning_workflow.py
│   │
│   ├── infrastructure/            # BMAD Layer 2: 基础设施层
│   │   ├── __init__.py
│   │   ├── persistence/
│   │   │   ├── database.py        # 成员1: PostgreSQL
│   │   │   ├── cache.py           # 成员1: Redis
│   │   │   ├── search.py          # 成员1: Elasticsearch
│   │   │   └── graph.py           # 成员3: Neo4j
│   │   ├── messaging/
│   │   │   ├── queue.py           # 成员2: RabbitMQ
│   │   │   └── events.py
│   │   ├── storage/
│   │   │   └── file_storage.py    # 成员2: MinIO
│   │   ├── ai/
│   │   │   ├── model_router.py    # 成员5: 模型路由
│   │   │   ├── context_manager.py # 成员5: 上下文管理
│   │   │   ├── ocr.py             # OCR服务
│   │   │   ├── tts.py             # TTS服务
│   │   │   └── llm_client.py
│   │   ├── security/
│   │   │   ├── auth.py            # 成员4: 安全认证
│   │   │   ├── rbac.py
│   │   │   └── audit.py
│   │   └── monitoring/
│   │       ├── metrics.py         # 成员6: Prometheus
│   │       ├── logging.py
│   │       └── tracing.py
│   │
│   └── interfaces/                # BMAD Layer 1: 接口适配层
│       ├── __init__.py
│       ├── api/
│       │   ├── __init__.py
│       │   ├── deps.py            # 依赖注入
│       │   ├── v1/
│       │   │   ├── __init__.py
│       │   │   ├── vocabulary.py  # 词汇API
│       │   │   ├── essay.py       # 作文API
│       │   │   ├── conversation.py # 对话API
│       │   │   ├── auth.py        # 认证API
│       │   │   └── recommend.py   # 推荐API
│       │   └── websocket/
│       │       └── voice_chat.py  # WebSocket语音对话
│       └── schemas/
│           ├── vocabulary.py
│           ├── essay.py
│           ├── conversation.py
│           └── common.py
│
├── tests/                         # 测试遵循SSD规范
│   ├── unit/                      # 单元测试
│   ├── integration/               # 集成测试
│   ├── e2e/                       # 端到端测试
│   └── fixtures/                  # 测试数据
│
├── specs/                         # SSD规范文档
│   ├── api_specs/                 # API规范
│   ├── domain_specs/              # 领域规范
│   └── test_specs/                # 测试规范
│
└── scripts/                       # 工具脚本
    ├── migrate.py                 # 数据迁移
    ├── seed.py                    # 数据初始化
    └── verify.py                  # 规范验证
```

### 3.3 阶段三：新模块整合（Week 3-4）

#### 3.3.1 整合优先级矩阵

```
                    高业务价值
                         ▲
                         │
    ┌────────────────────┼────────────────────┐
    │                    │                    │
    │   成员3 (知识图谱)  │   成员5 (模型路由)  │
    │   成员1 (数据库)    │   成员4 (安全认证)  │
    │                    │                    │
低技术风险◄──────────────┼────────────────────►高技术风险
    │                    │                    │
    │   成员7 (核心功能)  │   成员2 (基础设施)  │
    │   成员6 (监控日志)  │                    │
    │                    │                    │
    └────────────────────┼────────────────────┘
                         │
                         ▼
                    低业务价值

整合顺序：
1. 成员1 (数据库层) - 基础依赖
2. 成员3 (知识图谱) - 高价值低风险
3. 成员5 (模型路由) - 核心能力
4. 成员4 (安全认证) - 必须项
5. 成员2 (基础设施) - 补充完善
6. 成员6 (监控日志) - 最后补充
7. 成员7 (核心功能) - 基于以上构建
```

#### 3.3.2 整合规范（SSD契约）

```python
# 规范文件: specs/integration_contracts.py
# 每个模块必须实现的接口契约

from abc import ABC, abstractmethod
from typing import Protocol

# 成员1: 数据持久化契约
class DataPersistenceContract(Protocol):
    """数据持久化层必须实现的契约"""
    
    async def connect(self) -> None:
        """建立数据库连接"""
        ...
    
    async def disconnect(self) -> None:
        """关闭数据库连接"""
        ...
    
    async def health_check(self) -> bool:
        """健康检查"""
        ...

# 成员3: 知识图谱契约
class KnowledgeGraphContract(Protocol):
    """知识图谱模块必须实现的契约"""
    
    async def get_synonyms(self, word: str, top_k: int = 5) -> list[str]:
        """获取近义词"""
        ...
    
    async def get_cognates(self, word: str) -> list[dict]:
        """获取同根词"""
        ...
    
    async def recommend(self, user_id: str, n: int = 10) -> list[dict]:
        """个性化推荐"""
        ...

# 成员5: 模型路由契约
class ModelRoutingContract(Protocol):
    """模型路由模块必须实现的契约"""
    
    async def route(self, scene: str, prompt: str) -> str:
        """根据场景路由到合适的模型"""
        ...
    
    async def chat_with_context(
        self, 
        session_id: str, 
        message: str,
        context_window: int = 10
    ) -> str:
        """带上下文的对话"""
        ...
```

### 3.4 阶段四：代码质量检查与修复（Week 4-5）

#### 3.4.1 质量门禁（SSD自动化验证）

```yaml
# 规范文件: specs/quality_gates.yml
quality_gates:
  static_analysis:
    - tool: ruff
      rules: [E, F, I, N, W, UP, B, C4, SIM]
      max_line_length: 100
    
    - tool: mypy
      strict: true
      ignore_missing_imports: true
    
    - tool: bandit
      severity: [HIGH, MEDIUM]
  
  test_coverage:
    unit_tests:
      min_coverage: 80%
      required: true
    
    integration_tests:
      min_coverage: 60%
      required: true
    
    e2e_tests:
      critical_paths: [vocabulary_lookup, essay_grading, voice_chat]
  
  performance:
    api_latency:
      p50: < 100ms
      p95: < 300ms
      p99: < 500ms
    
    database_queries:
      max_query_time: 50ms
      n_plus_one_detection: true
  
  security:
    dependency_scan:
      tool: safety
      fail_on: [CRITICAL, HIGH]
    
    secret_detection:
      tool: detect-secrets
      fail_on: true
```

#### 3.4.2 代码修复清单

| 模块 | 问题类型 | 具体问题 | 修复方案 | 负责人 |
|------|----------|----------|----------|--------|
| 成员1 | 测试缺失 | 68个测试实际只有13个 | 补充测试文件 | 成员1 |
| 成员1 | 版本不一致 | PostgreSQL 15 vs 16 | 升级Docker配置 | 成员1 |
| 成员2 | 基础设施缺失 | infrastructure/目录为空 | 补充Docker Compose | 成员2 |
| 成员4 | 集成缺失 | 安全模块独立运行 | 集成到主项目 | 成员4 |
| 成员4 | 审计缺失 | 无审计日志系统 | 实现审计日志 | 成员4 |
| 成员5 | 测试不足 | 故障场景未测试 | 补充边界测试 | 成员5 |
| 成员6 | 实现缺失 | 仅文档无代码 | 立即投入开发 | 成员6 |
| 全局 | 类型注解 | 部分代码缺少类型 | 补全类型注解 | 全员 |

### 3.5 阶段五：核心功能提升（Week 5-6，3成员协作）

#### 3.5.1 协作模式（BMAD业务流驱动）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     3成员协作模式                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  成员A (词汇模块负责人)                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 职责：                                                              │   │
│  │ • 定义词汇领域模型 (domain/vocabulary.py)                           │   │
│  │ • 实现查词、词库生成、推荐复习业务逻辑                               │   │
│  │ • 集成成员1的数据库和成员3的知识图谱                                 │   │
│  │                                                                     │   │
│  │ 输入依赖：                                                          │   │
│  │ • 成员1: PostgreSQL + ES + Redis                                    │   │
│  │ • 成员3: Neo4j知识图谱 + 推荐引擎                                   │   │
│  │ • 成员5: 模型路由 (vocab场景)                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    │ 业务事件流                              │
│                                    ▼                                        │
│  成员B (作文模块负责人)                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 职责：                                                              │   │
│  │ • 定义作文领域模型 (domain/essay.py)                                │   │
│  │ • 实现OCR识别、作文批改、评分反馈业务逻辑                            │   │
│  │ • 集成成员2的消息队列进行异步批改                                    │   │
│  │                                                                     │   │
│  │ 输入依赖：                                                          │   │
│  │ • 成员2: RabbitMQ/Celery异步任务                                    │   │
│  │ • 成员5: 模型路由 (essay场景)                                       │   │
│  │ • OCR服务                                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    │ 业务事件流                              │
│                                    ▼                                        │
│  成员C (对话模块负责人)                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 职责：                                                              │   │
│  │ • 定义对话领域模型 (domain/conversation.py)                         │   │
│  │ • 实现语音对话、场景生成、上下文管理业务逻辑                         │   │
│  │ • 集成成员5的上下文管理和模型路由                                    │   │
│  │                                                                     │   │
│  │ 输入依赖：                                                          │   │
│  │ • 成员5: 模型路由 + 上下文管理 (chat场景)                           │   │
│  │ • TTS/ASR服务                                                      │   │
│  │ • WebSocket基础设施                                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  协作契约：                                                                  │
│  • 统一使用domain/application/infrastructure/interfaces分层               │
│  • 共享common schemas和utils                                              │
│  • 每日同步会议，代码评审互相覆盖                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 3.5.2 核心功能验收标准（SSD规范）

```yaml
# 规范文件: specs/core_features_acceptance.yml

features:
  vocabulary_module:
    description: 词汇模块
    owner: 成员A
    acceptance_criteria:
      - query_response_time_p95: < 100ms
      - cache_hit_rate: > 80%
      - synonym_accuracy: > 85%
      - recommendation_precision: > 30%
    dependencies:
      - member_1: [database, cache, search]
      - member_3: [knowledge_graph, recommendation]
      - member_5: [model_router]

  essay_module:
    description: 作文模块
    owner: 成员B
    acceptance_criteria:
      - ocr_accuracy: > 95%
      - grading_response_time: < 5s
      - score_consistency: > 90%
      - async_queue_reliability: > 99.9%
    dependencies:
      - member_2: [message_queue, file_storage]
      - member_5: [model_router]
      - ocr_service: available

  conversation_module:
    description: 对话模块
    owner: 成员C
    acceptance_criteria:
      - first_token_latency: < 500ms
      - voice_quality_mos: > 3.5
      - context_retention_accuracy: > 95%
      - interruption_recovery_time: < 1s
    dependencies:
      - member_5: [model_router, context_manager]
      - tts_service: available
      - asr_service: available
```

---

## 四、实施路线图

### 4.1 时间线（6周）

```
Week 1: 规范制定与死代码识别
├─ Day 1-2: 业务模型规范定义 (BMAD Layer 4)
├─ Day 3-4: 死代码扫描与标记
└─ Day 5: 规范评审与确认

Week 2-3: 旧模块清理与架构融合
├─ Week 2:
│  ├─ Day 1-2: 创建新目录结构
│  ├─ Day 3-4: 迁移有效代码
│  └─ Day 5: 清理死代码
├─ Week 3:
│  ├─ Day 1-3: 模块接口契约定义
│  └─ Day 4-5: 依赖注入配置

Week 3-4: 新模块整合
├─ Week 3 (后半):
│  ├─ 成员1整合 (数据库层)
│  └─ 成员3整合 (知识图谱)
└─ Week 4:
   ├─ 成员5整合 (模型路由)
   ├─ 成员4整合 (安全认证)
   └─ 成员2整合 (基础设施)

Week 4-5: 代码质量检查与修复
├─ Week 4 (后半):
│  ├─ 静态分析扫描
│  ├─ 测试覆盖率检查
│  └─ 性能基准测试
└─ Week 5:
   ├─ 问题修复
   ├─ 安全审计
   └─ 文档更新

Week 5-6: 核心功能提升 (3成员协作)
├─ Week 5 (后半):
│  ├─ 成员A: 词汇模块开发
│  ├─ 成员B: 作文模块开发
│  └─ 成员C: 对话模块开发
└─ Week 6:
   ├─ 集成测试
   ├─ 端到端测试
   └─ 性能优化与验收
```

### 4.2 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 成员2基础设施延迟 | 高 | 高 | 准备降级方案（单机Redis+RabbitMQ Docker） |
| 成员6监控缺失 | 高 | 中 | 使用基础日志+Prometheus快速方案 |
| 模块集成冲突 | 中 | 高 | 提前定义接口契约，每日同步 |
| 性能不达标 | 中 | 高 | 预留1周性能优化时间 |
| 测试覆盖不足 | 中 | 中 | 强制质量门禁，不达标不合并 |

---

## 五、成功指标

### 5.1 技术指标

```yaml
architecture_quality:
  test_coverage:
    unit: > 80%
    integration: > 60%
  
  code_quality:
    static_analysis_errors: 0
    type_coverage: > 90%
    cyclomatic_complexity: < 10 per function
  
  performance:
    api_p95_latency: < 300ms
    database_query_time: < 50ms
    cache_hit_rate: > 80%

module_integration:
  member_1: integrated  # 数据库+搜索
  member_2: integrated  # 基础设施
  member_3: integrated  # 知识图谱
  member_4: integrated  # 安全认证
  member_5: integrated  # 模型路由
  member_6: basic       # 监控日志（基础版）
```

### 5.2 业务指标

| 功能模块 | 验收标准 | 测试方法 |
|----------|----------|----------|
| 词汇查询 | P95延迟<100ms，准确率>95% | 自动化压力测试 |
| 作文批改 | OCR准确率>95%，评分一致性>90% | 人工+自动评估 |
| 语音对话 | 首Token<500ms，语音质量MOS>3.5 | 端到端测试 |
| 智能推荐 | 推荐精准度>30% | A/B测试 |

---

## 六、附录

### 6.1 参考文档

- `docs/team_performance_analysis.md` - 成员评估报告
- `docs/Detailed_System_Architecture.md` - 详细架构设计
- `.github/PULL_REQUEST_TEMPLATE_MODULE_E.md` - 模块E PR模板

### 6.2 工具链

```yaml
development_tools:
  ide: VS Code with Python extension
  linting: ruff, mypy, bandit
  testing: pytest, pytest-asyncio, pytest-cov
  formatting: ruff format
  git_hooks: pre-commit

ci_cd:
  static_analysis: automated on PR
  test_execution: automated on PR
  security_scan: automated on PR
  deployment: manual trigger
```

### 6.3 沟通机制

- **每日站会**: 15分钟，同步进度与阻塞
- **代码评审**: 所有PR需至少1人评审
- **架构评审**: 重大变更需架构评审会议
- **文档更新**: 代码变更必须同步更新文档

---

*本文档遵循SSD原则，所有规范变更需通过评审流程*
*架构设计遵循BMAD四层模型，业务逻辑独立于技术实现*
