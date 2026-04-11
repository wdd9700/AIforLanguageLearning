# Phase 4 核心功能交接文档 — 作文模块（Essay）

**交接日期**: 2026年4月12日  
**负责成员**: 成员 B（作文模块）  
**前置条件**: Phase 3 基础设施加固已完成，测试全绿（`pytest tests/ -m "not integration"` = 97 passed）

---

## 1. 工作范围

负责实现以下核心能力：
1. **作文提交** — 支持文本/图片提交，图片经 MinIO 存储后触发异步批改
2. **OCR 预处理** — 复用现有 `ocr.py` 提取图片中的作文文本
3. **异步作文批改** — 填充 Celery `grade_essay_task`，对接 LLM 综合批改
4. **多维度评分** — 内容(30%)、结构(25%)、语言(25%)、语法(20%)
5. **结果查询** — 查询作文及批改结果，支持结构化展示

---

## 2. 当前基座状态（已就绪，可直接使用）

### 2.1 数据模型
- **文件**: `backend_fastapi/app/models.py`
- **相关模型**:
  - `EssaySubmission` — 作文提交记录（`ocr_text`, `language`, `session_id`, `conversation_id`）
  - `EssayResult` — 批改结果（`score`, `result` JSON）

### 2.2 基础设施封装
- **MinIO 存储** — `backend_fastapi/app/infrastructure/storage/minio_storage.py`
  - `MinIOStorage` 已封装上传、分片上传、预签名 URL
  - `get_minio_storage()` 从 `settings` 自动读取 endpoint/credentials
- **文件上传路由** — `backend_fastapi/app/interfaces/storage_router.py`
  - `POST /api/v1/upload` — 单文件上传
  - `POST /api/v1/upload/multipart/init` / `complete` — 分片上传
  - `POST /api/v1/upload/presigned-url` — 预签名 URL
- **Celery 任务** — `backend_fastapi/app/infrastructure/messaging/tasks.py`
  - `grade_essay_task` 当前为 stub，需要你填充完整业务逻辑
  - `celery_app.py` 已配置 DLQ、队列路由、重试策略
- **OCR 服务** — `backend_fastapi/app/ocr.py`
  - 已封装 `extract_text_from_image()`，支持 PaddleOCR
- **LLM 服务** — `backend_fastapi/app/llm.py`
  - `chat_complete()`, `grade_essay()` 已封装 Kimi API 调用
- **任务投递路由** — `backend_fastapi/app/interfaces/tasks_router.py`
  - `POST /api/v1/tasks/essay` 已存在，可直接复用

### 2.3 现有路由
- `backend_fastapi/app/routers/essays.py` — 已有部分作文相关路由，请在此基础上扩展
- `backend_fastapi/app/interfaces/storage_router.py` — 文件上传接口已就绪

---

## 3. 需要完成的工作

### 3.1 作文提交 API
**路由建议**: `POST /api/v1/essays`

**实现要求**:
1. 支持两种提交方式：
   - **纯文本**: 直接接收 `content` 字段
   - **图片**: 接收 `image_url` 或调用 `storage_router` 先上传图片，返回图片 key
2. 创建 `EssaySubmission` 记录（`ocr_text` 在图片提交时为空，由 Celery 任务填充）
3. 投递 Celery 任务 `grade_essay_task.delay(submission_id, content_or_image_key)`
4. 返回提交成功响应，包含 `submission_id` 和 `task_id`

**接口契约**:
```json
// Request (文本)
{
  "content": "In recent years, online education has become increasingly popular...",
  "language": "en"
}

// Request (图片)
{
  "image_key": "essays/user_123_20260412.jpg",
  "language": "en"
}

// Response
{
  "success": true,
  "data": {
    "submission_id": 42,
    "task_id": "celery-task-id-xxx",
    "status": "submitted"
  }
}
```

### 3.2 作文批改 Celery 任务
**文件**: `backend_fastapi/app/infrastructure/messaging/tasks.py`

**实现要求**:
1. 若输入为图片 key，调用 `MinIOStorage` 下载图片，再调用 `ocr.extract_text_from_image()` 提取文本
2. 调用 `llm.grade_essay()` 进行综合批改（或 `llm.chat_complete()` 自定义 Prompt）
3. 将 LLM 返回的批改结果解析为结构化数据，计算多维度评分
4. 写入 `EssayResult` 表

**批改流程**:
```
EssaySubmission 创建
    │
    ▼
┌─────────────────┐
│  图片? → OCR    │
│  提取文本        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  可靠语料库API   │  (可选，可先跳过，直接 LLM)
│  拼写/基础语法   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LLM 综合批改    │
│  grade_essay()  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  多维度评分      │
│  内容/结构/语言/语法│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  写入 EssayResult│
└─────────────────┘
```

### 3.3 多维度评分算法
**文件建议**: `backend_fastapi/app/domain/essay_scoring.py`

**评分维度**:
| 维度 | 权重 | 计算方式（建议） |
|------|------|------------------|
| 内容 (Content) | 30% | LLM 评估得分 × 0.3 |
| 结构 (Structure) | 25% | LLM 评估得分 × 0.25 |
| 语言 (Language) | 25% | 词汇丰富度/句式多样性得分 × 0.25 |
| 语法 (Grammar) | 20% | 语法错误密度/拼写准确性得分 × 0.2 |

**总分** = Σ(维度得分 × 权重)，映射等级：
- 9-10: A+
- 8-9: A
- 7-8: B+
- 6-7: B
- 5-6: C
- <5: D

**结果存储格式** (`EssayResult.result` JSON):
```json
{
  "dimensions": {
    "content": {"score": 8.0, "weight": 0.30, "weighted": 2.40},
    "structure": {"score": 7.0, "weight": 0.25, "weighted": 1.75},
    "language": {"score": 8.0, "weight": 0.25, "weighted": 2.00},
    "grammar": {"score": 6.0, "weight": 0.20, "weighted": 1.20}
  },
  "total_score": 7.35,
  "grade": "B+",
  "feedback": "...",
  "suggestions": ["...", "..."],
  "corrected_text": "..."
}
```

### 3.4 查询批改结果 API
**路由建议**: `GET /api/v1/essays/{submission_id}`

**实现要求**:
1. 根据 `submission_id` 查询 `EssaySubmission` 和关联的 `EssayResult`
2. 若 `EssayResult` 不存在，返回 `status: "grading"`
3. 若已批改完成，返回完整评分结果

**接口契约**:
```json
// Response (批改中)
{
  "success": true,
  "data": {
    "submission_id": 42,
    "status": "grading",
    "created_at": "2026-04-12T10:00:00Z"
  }
}

// Response (已完成)
{
  "success": true,
  "data": {
    "submission_id": 42,
    "status": "completed",
    "ocr_text": "In recent years...",
    "result": {
      "total_score": 7.35,
      "grade": "B+",
      "feedback": "...",
      "dimensions": { ... }
    },
    "created_at": "2026-04-12T10:00:00Z",
    "completed_at": "2026-04-12T10:00:05Z"
  }
}
```

---

## 4. 依赖关系

| 依赖模块 | 状态 | 说明 |
|----------|------|------|
| MinIO 存储 | ✅ 就绪 | `minio_storage.py` + `storage_router.py` |
| Celery 任务 | ✅ 就绪 | 需要填充 `grade_essay_task` |
| OCR | ✅ 就绪 | `ocr.py` 已封装 |
| LLM | ✅ 就绪 | `llm.py` 已封装 |
| 任务投递路由 | ✅ 就绪 | `tasks_router.py` 已存在 |

---

## 5. 验收标准

- [ ] `POST /api/v1/essays` 支持文本和图片两种提交方式
- [ ] 图片提交后自动触发 Celery 任务，OCR 提取文本 + LLM 批改
- [ ] `GET /api/v1/essays/{id}` 能正确返回批改中/已完成状态
- [ ] 多维度评分算法实现，总分和等级映射正确
- [ ] `EssayResult` 数据库存储结构符合 JSON Schema
- [ ] 新增测试文件 `tests/test_essay_module.py`，覆盖提交、查询、评分计算
- [ ] `pytest tests/ -m "not integration"` 仍然全绿

---

## 6. 注意事项与风险

1. **OCR 失败回退**: 若 `ocr.py` 提取图片文本失败（如图片模糊），Celery 任务应记录错误状态，而不是无限重试。
2. **MinIO 下载**: 从 MinIO 下载图片时使用 `get_minio_storage().generate_presigned_url()` 或直接通过内部网络访问。
3. **LLM Token 成本**: 作文批改较长文本时 Token 消耗大，建议在 Prompt 中限制输入长度（如最多 2000 词），超长时截断并提示用户。
4. **Celery 任务幂等性**: `grade_essay_task` 应保证幂等，避免同一 `submission_id` 被多次批改产生重复 `EssayResult`。
5. **评分算法演进**: 第一阶段可先完全依赖 LLM 返回各维度评分，后续再引入规则引擎（如词汇丰富度 TTR 计算）做混合评分。

---

## 7. 参考文档

- `docs/Detailed_System_Architecture.md` 第 2 章（作文模块详细架构）
- `backend_fastapi/app/infrastructure/messaging/tasks.py`
- `backend_fastapi/app/infrastructure/storage/minio_storage.py`
- `backend_fastapi/app/ocr.py`
- `backend_fastapi/app/llm.py`
- `backend_fastapi/app/models.py`（`EssaySubmission`, `EssayResult`）
