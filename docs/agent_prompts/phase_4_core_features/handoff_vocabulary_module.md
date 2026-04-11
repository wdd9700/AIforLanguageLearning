# Phase 4 核心功能交接文档 — 单词模块（Vocabulary）

**交接日期**: 2026年4月12日  
**负责成员**: 成员 A（单词模块）  
**前置条件**: Phase 3 基础设施加固已完成，测试全绿（`pytest tests/ -m "not integration"` = 97 passed）

---

## 1. 工作范围

负责实现以下核心能力：
1. **查词搜索** — ES 模糊搜索 + Redis Cache-Aside + Neo4j 知识图谱关联
2. **词库生成** — 调用 LLM 生成主题词汇，Celery 异步批量入库
3. **推荐复习** — 基于 SM-2 算法返回当日待复习单词，提交复习结果更新间隔

---

## 2. 当前基座状态（已就绪，可直接使用）

### 2.1 数据模型
- **文件**: `backend_fastapi/app/domain/models.py`
- **相关模型**:
  - `VocabularyItem` — 用户个人词汇表（含 `word`, `definition`, `mastery_level`, `next_review_at`）
  - `User`, `StudentProfile` — 用户基础信息
- **文件**: `backend_fastapi/app/models.py`
  - `PublicVocabEntry` — 公共词库表
  - `UserVocabQuery` — 用户查词历史记录表

### 2.2 基础设施封装
- **ES 搜索** — `backend_fastapi/app/infrastructure/persistence/search/es_client.py`
  - `ESClient` / `get_es_client()`
  - `ensure_index()` / `index_document()` / `search_vocabulary()`
  - 索引名: `aifl_vocabulary`，字段: `word^3`, `definition`, `tags`
- **Redis 缓存** — `backend_fastapi/app/infrastructure/persistence/cache/redis_cache.py`
  - `RedisCache` 已支持 `get()`, `set()`, `delete()`, `lock()`, `get_or_set()`
  - 连接失败时自动静默降级，不会阻塞业务
- **Neo4j 知识图谱** — `backend_fastapi/app/domain/knowledge_graph/`
  - `client.py` 带 `NEO4J_AVAILABLE` 兼容层，无 Neo4j 时优雅降级
  - `interfaces/knowledge_graph_router.py` 已注册路由
- **Celery 任务** — `backend_fastapi/app/infrastructure/messaging/`
  - `celery_app.py` 已配置 DLQ、队列优先级
  - `tasks.py` 中 `generate_daily_vocab_task` 当前为 stub，需要你填充业务逻辑
- **SM-2 算法** — `backend_fastapi/app/domain/srs/sm2.py`
  - 已迁移，可直接调用 `sm2_review(interval, repetition, ease, quality)`

### 2.3 现有路由
- `backend_fastapi/app/routers/vocab.py` — 已有部分词汇相关路由，请在此基础上扩展或重构
- `backend_fastapi/app/interfaces/tasks_router.py` — 已有 `/api/v1/tasks/vocab` 任务投递接口

---

## 3. 需要完成的工作

### 3.1 查词搜索 API
**路由建议**: `POST /api/v1/vocab/search`

**流程**:
```
用户输入查询词
    │
    ▼
┌─────────────────┐
│  输入预处理      │  拼写纠错、词干提取（可选，可先简化）
└────────┬────────┘
         │
         ▼
┌─────────────────┐     未命中
│  Redis缓存检查   │ ───────────► ┌─────────────────┐
│  key: vocab:{q} │              │  ES 模糊搜索     │
└────────┬────────┘              │  multi_match     │
         │ 命中                  │  fuzziness: AUTO │
         ▼                       └────────┬────────┘
┌─────────────────┐                      │
│  返回缓存结果    │                      ▼
└─────────────────┘           ┌─────────────────┐
                              │  Neo4j KG 查询  │
                              │  同根词/同义词  │
                              │  （降级时跳过） │
                              └────────┬────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │  PostgreSQL     │
                              │  查询详细释义   │
                              │  （可选回源）   │
                              └────────┬────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │  聚合排序        │
                              │  写入Redis缓存   │
                              │  返回结果        │
                              └─────────────────┘
```

**接口契约**:
```json
// Request
{
  "query": "accommodate",
  "fuzzy": true,
  "include_relations": true
}

// Response
{
  "success": true,
  "data": {
    "results": [
      {
        "word": "accommodate",
        "definition": "to provide lodging or sufficient space for",
        "pronunciation": "/əˈkɒmədeɪt/",
        "example": "The hotel can accommodate up to 500 guests.",
        "tags": ["verb", "formal"],
        "relations": {
          "synonyms": ["adapt", "adjust"],
          "antonyms": ["disoblige"],
          "root_words": ["commodious"]
        }
      }
    ],
    "total": 1,
    "cached": false
  }
}
```

### 3.2 词库生成 API
**路由建议**: `POST /api/v1/vocab/generate`

**实现要求**:
1. 接收参数: `theme` (主题), `difficulty` (难度), `count` (数量，默认 20)
2. 调用 `llm.py` 中的 `chat_complete()` 或 `generate_definition()` 生成词汇列表
3. 将生成任务异步投递到 Celery（复用 `generate_daily_vocab_task` 或新建任务）
4. Celery Worker 中：解析 LLM 输出 → 标签归类 → 写入 PostgreSQL + 同步索引到 ES

**接口契约**:
```json
// Request
{
  "theme": "business english",
  "difficulty": "intermediate",
  "count": 20
}

// Response (同步返回任务ID)
{
  "success": true,
  "data": {
    "task_id": "abc-123",
    "status": "submitted"
  }
}
```

### 3.3 推荐复习 API
**路由建议**:
- `GET /api/v1/vocab/review` — 获取今日待复习单词
- `POST /api/v1/vocab/review` — 提交复习结果，更新 SM-2 参数

**实现要求**:
1. `GET /review` 查询当前用户的 `VocabularyItem`，筛选 `next_review_at <= now()`
2. 按 `mastery_level` 排序，返回 Top-N
3. `POST /review` 接收: `vocab_id`, `quality` (0-5 评分)
4. 调用 `sm2.py` 计算新的 `interval`, `repetition`, `ease_factor`
5. 更新 `VocabularyItem` 的 `next_review_at` 和 `mastery_level`

**接口契约**:
```json
// GET Response
{
  "success": true,
  "data": {
    "due_today": 12,
    "words": [
      {
        "id": 1,
        "word": "accommodate",
        "definition": "...",
        "mastery_level": 2
      }
    ]
  }
}

// POST Request
{
  "vocab_id": 1,
  "quality": 4
}
```

---

## 4. 依赖关系

| 依赖模块 | 状态 | 说明 |
|----------|------|------|
| ES 搜索 | ✅ 就绪 | `es_client.py` 可直接调用 |
| Redis 缓存 | ✅ 就绪 | `redis_cache.py` 可直接调用 |
| Neo4j KG | ✅ 就绪 | 带降级保护，可安全调用 |
| Celery | ✅ 就绪 | 需要填充 `generate_daily_vocab_task` |
| SM-2 算法 | ✅ 就绪 | `domain/srs/sm2.py` |
| LLM 调用 | ✅ 就绪 | `llm.py` 已封装 Kimi API |

---

## 5. 验收标准

- [ ] `POST /api/v1/vocab/search` 可用，未登录用户返回 401，正常查询返回结构化结果
- [ ] ES 搜索响应时间 < 200ms（本地单节点）
- [ ] Redis 缓存命中时，搜索响应时间 < 50ms
- [ ] `POST /api/v1/vocab/generate` 能成功投递 Celery 任务，Worker 消费后数据写入 PG + ES
- [ ] `GET /api/v1/vocab/review` 正确返回当日待复习单词
- [ ] `POST /api/v1/vocab/review` 正确更新 SM-2 间隔和 `mastery_level`
- [ ] 新增测试文件 `tests/test_vocab_module.py`，覆盖率 > 80%
- [ ] `pytest tests/ -m "not integration"` 仍然全绿

---

## 6. 注意事项与风险

1. **Neo4j 降级**: 本地开发时若 Neo4j 未启动，`NEO4J_AVAILABLE=False`，知识图谱关联字段应返回空列表而非报错。
2. **ES 索引初始化**: 首次运行前需要调用 `ensure_index()` 创建索引。可在应用启动 lifespan 中自动执行，或在测试 fixture 中处理。
3. **LLM 输出解析**: 词库生成时 LLM 可能返回非标准 JSON，建议 Prompt 中明确要求 JSON 格式，并做容错解析。
4. **并发写入**: Celery Worker 批量写入 ES 时，注意 ES 的 `index_document()` 是单文档接口，大量数据时建议批量 `bulk()` 优化（可延后优化）。
5. **Cache-Aside 一致性**: 词汇数据更新后，需要同步清除或更新 Redis 缓存，避免脏读。

---

## 7. 参考文档

- `docs/Detailed_System_Architecture.md` 第 1 章（单词模块详细架构）
- `backend_fastapi/app/infrastructure/persistence/search/es_client.py`
- `backend_fastapi/app/infrastructure/persistence/cache/redis_cache.py`
- `backend_fastapi/app/domain/srs/sm2.py`
- `backend_fastapi/app/infrastructure/messaging/tasks.py`
