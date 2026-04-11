# 阶段1 执行结果汇总

## Agent 执行结果汇总 1/3

**执行时间**: 2026-04-12
**Agent 名称**: 代码考古学家 (expert_01_archaeologist)
**Prompt 文件**: `docs/agent_prompts/phase_1_dead_code_cleanup/expert_01_archaeologist.md`

### 主要结论
1. 旧 `backend/src/` 共 **63个文件，~10,243 LOC**，其中约 **65% 是死代码**
2. **已迁移到 FastAPI 的功能**：路由层面约60%，数据模型/业务逻辑层面仅约30%
3. **必须保留并迁移的模块**：`auth/`（JWT体系）、`models/`（SRS算法、用户/学生/学习路径模型）、`database/`（Schema参考）
4. **建议废弃的模块**：`api/`、`controllers/`、`infra/`、`managers/`（除Prompt模板外）、`middleware/`、`orchestrator/`、`security/`、`services/`、`shared/`、`softbus/`、`utils/`
5. **最紧迫缺口**：FastAPI 的 `auth.py` 仍是硬编码 `admin/admin`，严重阻碍上线

### 关键发现
- `auth/jwt.ts` 和 `auth/password.ts` 实现了完整的 JWT Token 对（access+refresh）、密码哈希、密码强度校验，FastAPI 中完全缺失
- `models/vocabulary.ts` 包含简化版 **SM-2 间隔重复算法**（`updateMastery`、`getDueWords`），FastAPI 中无生词本SRS功能
- `database/db.ts` 定义了9张完整表（`users`, `sessions`, `students`, `learning_paths`, `vocabulary`, `essays`, `learning_records`, `language_profiles`, `llm_finetune_data`），FastAPI 仅实现了5张极简表
- `services/` 中的 ASR/TTS/OCR/LLM 桥接服务已被 FastAPI 原生 Python 实现完全替代，可直接废弃
- `softbus/`（ZeroMQ+mDNS，~1,500 LOC）和 `orchestrator/`（自研消息编排引擎）在当前单体 FastAPI 架构下完全无用
- `controllers/admin.controller.ts` 中的备份、日志、用户管理、服务监控功能在 FastAPI 中完全缺失

### 风险与建议
1. **数据库 Schema 不兼容风险**：新旧表结构差异巨大，若已有生产数据需专门迁移脚本
2. **认证降级风险**：FastAPI 当前硬编码 admin/admin，暴露公网前必须优先修复
3. **测试依赖风险**：`test-quick.ts` 和 `test-integration.ts` 仍引用旧 `ServiceManager`，清理前需同步更新

### 下一步行动
1. 执行 `expert_02_migration_planner.md` 制定详细迁移计划
2. 基于迁移计划，后续执行 `subagent_01_migrator.md` 进行实际代码迁移
3. P0优先迁移：认证体系 → 核心数据模型/SRS算法 → Admin后台

---

## Agent 执行结果汇总 2/3

**执行时间**: 2026-04-12
**Agent 名称**: 迁移规划师 (expert_02_migration_planner)
**Prompt 文件**: `docs/agent_prompts/phase_1_dead_code_cleanup/expert_02_migration_planner.md`

### 主要结论
1. **迁移总工时估算**: ~12天（1名后端工程师全职），分为6个里程碑（M1~M6）
2. **迁移顺序已按依赖拓扑排序**: Schema参考 → 认证体系 → 用户/学生模型 → SM-2 SRS算法 → 学习路径 → Admin后台 → 死代码清理
3. **P0 优先项**: 认证体系（JWT+密码哈希）和核心数据模型（9张旧表 SQLModel 化）必须在最前面完成
4. **数据迁移风险可控**: 旧 `bcryptjs` 哈希与 Python `passlib[bcrypt]` 兼容，用户密码可直接迁移；时间戳需毫秒→datetime转换；`essays` 单表需拆分为新 `essay_submissions` + `essay_results`
5. **明确废弃范围**: 除 `auth/`、`models/`（部分）、`database/`（Schema参考）、`controllers/admin.controller.ts` 外，其余旧 `backend/src/` 模块均列入"不做"清单

### 关键迁移策略
- **认证体系**: 将 `auth/jwt.ts` + `auth/password.ts` 翻译为 Python（`python-jose` + `passlib`），替换硬编码 `admin/admin`，保持 `LoginResponse` 响应格式不变
- **数据模型**: 旧 `database/db.ts` 的9张表全部翻译为 SQLModel，FastAPI 现有5张表保留，统一纳入 `domain/models`
- **SM-2 算法**: 精确迁移 `models/vocabulary.ts` 中的 `updateMastery`/`getDueWords` 逻辑到 `domain/srs/sm2.py`，单元测试覆盖边界条件
- **Admin 后台**: 废弃旧自研管理器框架（Config/Service/Backup/Cleanup Manager），用 FastAPI 原生方式重写等价功能（配置读取、服务状态探测、备份/恢复、日志管理、用户列表）

### 兼容性保障
- `compat_legacy.py` 已覆盖的5个接口（词汇查询、OCR、作文批改、学习统计、学习分析）必须保持行为一致
- 新增兼容接口：`POST /api/auth/register`、`POST /api/auth/refresh`，以及 Admin 后台全套 `/api/admin/*` 接口
- 前端适配点：JWT Token 替换 `dev-token-*`、Admin 路径和响应结构保持一致

### 风险与缓解
| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 认证迁移安全漏洞 | 中 | 高 | 标准库实现、环境变量密钥、登录速率限制 |
| 旧 SQLite 数据丢失 | 低 | 高 | 迁移前全量备份、事务化脚本、抽样校验 |
| SM-2 算法翻译偏差 | 中 | 中 | 单元测试覆盖、与旧代码输出交叉比对 |
| 死代码误删 | 中 | 中 | 按清单执行、删除前全局 grep 确认、保留 Git 历史 |
| Admin 备份恢复损坏数据库 | 低 | 高 | 恢复前自动快照、维护模式、提供回滚脚本 |

### 下一步行动
1. 执行 `subagent_01_migrator.md` 按本计划进行实际代码迁移
2. 优先启动 M1（Schema 补全）和 M2（认证体系），两者可并行
3. 在 M5 完成数据迁移脚本和 API 兼容性回归测试后，再执行 M6 死代码清理

---

## Agent 执行结果汇总 3/3

**执行时间**: 2026-04-12
**Agent 名称**: 代码迁移工 (subagent_01_migrator)
**Prompt 文件**: `docs/agent_prompts/phase_1_dead_code_cleanup/subagent_01_migrator.md`

### 执行摘要
- 迁移模块数: 6
- 新增文件数: 17
- 修改文件数: 5
- 删除/标记死代码数: 0（本次未执行清理，按规划师建议留待 M6）
- ruff 检查状态: 通过（新迁移代码 0 errors）
- mypy 检查状态: 通过（新迁移代码 0 errors）

### 目录结构变更

```
backend_fastapi/app/
├── domain/
│   ├── __init__.py
│   ├── models.py              # User, StudentProfile, VocabularyItem, LearningRecord, LearningPath
│   └── srs/
│       ├── __init__.py
│       └── sm2.py             # 简化 SM-2 间隔重复算法
├── application/
│   ├── __init__.py
│   ├── db_student.py          # 学生档案 Upsert/Query
│   ├── db_vocabulary.py       # 生词本 Add/GetDue/Review
│   └── db_learning.py         # 学习记录与路径 CRUD
├── infrastructure/
│   ├── __init__.py
│   ├── security.py            # JWT + passlib[bcrypt] + 密码强度校验
│   ├── dependencies.py        # get_current_user / get_optional_user
│   └── db_user.py             # 用户表底层操作
├── interfaces/
│   ├── __init__.py
│   ├── auth_router.py         # /api/auth/* (register/login/refresh/me/profile/vocabulary)
│   └── admin_router.py        # /api/admin/* (config/prompts/services/backups/logs/users/system-stats/cleanup)
└── [修改]
    ├── db.py                  # 导入 domain models 确保建表
    ├── main.py                # 注册 auth_router / admin_router
    ├── settings.py            # 新增 jwt_secret 配置项
    └── context_store.py       # 修复循环导入（局部导入 + 清理重复方法）
```

### 详细迁移记录

#### 1. 认证体系 (JWT + bcrypt)
**旧位置**: `backend/src/auth/jwt.ts` + `backend/src/auth/password.ts`
**新位置**: `backend_fastapi/app/infrastructure/security.py`
**迁移策略**: 翻译重写
**变更说明**:
- 使用 `python-jose` 实现 Access/Refresh Token 签发与解码
- 使用 `passlib[bcrypt]` 替换 `bcryptjs`，经测试与旧哈希兼容
- 在 `settings.py` 中新增 `jwt_secret` 字段，默认回退与旧 `.env` 一致
- 修复了 FastAPI 端原先硬编码 `admin/admin` 的问题

**代码示例**:
```python
# app/infrastructure/security.py
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, _get_secret(), algorithm=ALGORITHM)
```

#### 2. 用户模型
**旧位置**: `backend/src/models/user.ts`
**新位置**: `backend_fastapi/app/domain/models.py` (User) + `app/infrastructure/db_user.py`
**迁移策略**: 翻译为 SQLModel + 拆分底层数据访问
**变更说明**:
- `User` 表结构保持与旧后端一致（username/email/password_hash/created_at/updated_at）
- 时间戳由毫秒整数改为 `datetime.utcnow()`
- 提供 `create_user`、`verify_credentials`、`list_users` 等原子操作

#### 3. 学生档案模型
**旧位置**: `backend/src/models/student.ts`
**新位置**: `backend_fastapi/app/domain/models.py` (StudentProfile) + `app/application/db_student.py`
**迁移策略**: 翻译重写
**变更说明**:
- 保留 `level`、`goals`（JSON）、`interests`（JSON）字段
- `upsert_profile` 实现与旧代码一致的“存在则更新，不存在则插入”逻辑

#### 4. 生词本 / SM-2 SRS
**旧位置**: `backend/src/models/vocabulary.ts`
**新位置**:
- `backend_fastapi/app/domain/models.py` (VocabularyItem)
- `backend_fastapi/app/domain/srs/sm2.py`
- `backend_fastapi/app/application/db_vocabulary.py`
**迁移策略**: 精确翻译算法 + SQLModel 化
**变更说明**:
- `updateMastery` / `getDueWords` 逻辑完整迁移到 `sm2.py` + `db_vocabulary.py`
- 间隔计算规则保持不变：答对 `days = 2^(level-1)`，答错 `10 分钟`
- 新增 `review_word` 封装事务级复习更新

**代码示例**:
```python
# app/domain/srs/sm2.py
def calculate_next_review(mastery_level: int, correct: bool) -> tuple[int, datetime]:
    now = datetime.utcnow()
    if correct:
        new_level = mastery_level + 1
        days = 2 ** (new_level - 1) if new_level > 0 else 1
        next_review = now + timedelta(days=days)
    else:
        new_level = max(0, mastery_level - 1)
        next_review = now + timedelta(minutes=10)
    return new_level, next_review
```

#### 5. 学习记录与学习路径
**旧位置**: `backend/src/models/learning-record.ts` + `backend/src/models/learning-path.ts`
**新位置**: `backend_fastapi/app/domain/models.py` + `app/application/db_learning.py`
**迁移策略**: 翻译重写
**变更说明**:
- `LearningRecord` 统一存储各类学习活动，metadata 字段映射为 `meta_data`（避免 SQLAlchemy 保留字冲突）
- `LearningPath` 保留 `milestones` JSON 数组、`status`、`progress`

#### 6. Admin 后台
**旧位置**: `backend/src/controllers/admin.controller.ts` + `backend/src/api/routes/admin.ts`
**新位置**: `backend_fastapi/app/interfaces/admin_router.py`
**迁移策略**: 废弃旧 Manager 框架，用 FastAPI 原生方式重写等价功能
**变更说明**:
- 配置管理：读取 `settings` + 运行时写入 `runtime_config.json`
- Prompt 管理：直接读写 `app/prompts/*.json`
- 备份/恢复：操作 SQLite 数据库文件，恢复前自动创建快照
- 日志管理：读取/清空 `logs/app.log`
- 用户管理：分页列表、重置密码、删除用户
- 系统状态：使用 `psutil` 获取 CPU/内存/进程信息
- 当前采用最小可用权限策略：仅 `username == "admin"` 可访问（与旧后端 Basic Auth 等价）

### 死代码清理记录

| 旧位置 | 处理方式 | 理由 |
|--------|----------|------|
| 本次未执行清理 | — | 按迁移规划师建议，死代码清理纳入 M6，待数据迁移和回归测试完成后再执行，避免误删 |

### 测试覆盖

| 模块 | 测试文件 | 覆盖类型 | 状态 |
|------|----------|----------|------|
| 认证体系 (注册/登录/刷新/Me) | `tests/test_auth_migration.py` | 单元/集成 | 通过 |
| 学生档案 (获取/更新) | `tests/test_auth_migration.py` | 单元/集成 | 通过 |
| Admin 后台 (用户列表) | `tests/test_auth_migration.py` | 单元/集成 | 通过 |
| SM-2 SRS 算法 | `tests/test_srs_sm2.py` | 单元 | 通过 |

### 质量检查结果

#### ruff（新迁移代码范围）
```
All checks passed!
```

#### mypy（新迁移代码范围）
```
Success: no issues found in 15 source files
```

### 遇到的问题与解决方案

1. **问题**: `passlib[bcrypt]` 与 `bcrypt 5.0.0` 存在兼容性错误（`ValueError: password cannot be longer than 72 bytes`）
   **解决**: 降级 `bcrypt` 到 `4.3.0`，哈希与验证恢复正常

2. **问题**: `context_store.py` 与 `model_router.py` 存在循环导入（`ConversationContext`）
   **解决**: 在 `context_store.py` 中将 `ConversationContext` / `ConversationMessage` 改为方法内局部导入；同时清理了文件中重复定义的 `RedisContextStore` 方法

3. **问题**: `LearningRecord` 模型使用字段名 `metadata`，与 SQLAlchemy Declarative API 保留字冲突
   **解决**: 字段名改为 `meta_data`，并通过 `sa_column=Column("metadata", JSON)` 保持数据库列名不变

4. **问题**: `email-validator` 未安装导致 `EmailStr` 报错
   **解决**: 安装 `email-validator` 包

### 未完成任务

1. **数据迁移脚本** — 旧 SQLite 数据（毫秒时间戳、旧 essays 表结构）向新 SQLModel 表的迁移脚本尚未编写，阻塞原因：需确认生产环境是否有存量数据
2. **Admin 角色/权限细化** — 当前仅通过 `username == "admin"` 判断，阻塞原因：需产品确认 RBAC 设计
3. **旧 backend/src/ 死代码清理** — 按规划师建议留待 M6 执行

### 下一步建议

1. 运行完整回归测试（包含 `compat_legacy.py` 兼容接口），确认前端登录流程正常
2. 若存在旧数据库生产数据，优先编写并执行数据迁移脚本（时间戳转换 + essays 表拆分）
3. 在前端将 `dev-token-*` 替换为新的 JWT Bearer Token 机制
4. 进入 M6 死代码清理阶段，按清单安全删除旧 `backend/src/` 中确认废弃的模块

---

*[本文件将持续更新阶段1的所有Agent执行结果]*
