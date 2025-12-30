# 项目迁移开发里程碑（后端重构：FastAPI + OpenAI兼容LLM + 多模态编排）

日期：2025-12-25

## 目标与约束

### 目标
- 回归“可运行、可测试、可观测”的最小闭环，显著降低 bug 存量。
- 用成熟开源组件替代自研实现：认证、配置、数据库迁移、日志、可观测、任务处理等。
- 保持前端**暂不变动**：后端提供与现有前端可对接的 HTTP + WebSocket 能力（尤其是 Markdown 结果推送与语音流）。
- LLM 通过 LM Studio 的 OpenAI 兼容接口接入，支持模型路由（主模型/分析模型）。

### 非目标（当前阶段不做）
- 不进行前端框架迁移（React/Vue 均不在本里程碑范围）。
- 不追求一次性实现“完美流式 TTS/ASR”；先以端到端可用为验收，再做性能与低延迟。

## 功能拆分 -> 技术能力映射

下面按你给出的 4 个场景拆解后端需要具备的“可复用能力”。

### A. 单词查询（文字/图片）
必需能力：
- 公共词库查询（全文检索/模糊匹配/去重）
- 未命中时调用主模型生成 Markdown 结果
- OCR（图片->文本）
- 结果通过 WebSocket 实时推送（支持中间态：OCR进度/LLM生成进度/最终结果）
- 双库写入：公共库写入“已生成的词条”，用户库写入“查询历史（含时间戳、来源）”

### B. 作文批改
必需能力：
- OCR（图片->文本）
- 调用分析模型输出结构化 JSON（评分/建议/错误列表/重写建议等）
- 将结构化结果 + 原文持久化到用户库
- 可选：将摘要/关键指标缓存，便于统计与可视化

### C. 场景语音对话（低延迟、流式）
必需能力：
- 生成 system prompt（分析模型/或主模型的“提示词扩展任务”）
- WebSocket 双向通道：前端推送音频分片；后端回推 ASR 文本/LLM token/TTS 音频分片
- VAD（判停）/或 ASR 停顿判定
- 事件协议：序列号、幂等、断线重连恢复（至少支持“从 last_seq 恢复”）
- 全双工（Barge-in）：用户说话可随时打断系统播报；服务端必须能取消 LLM/TTS 任务并停止继续推送
- 对话结束后：对话分析（分析模型）+ 用户库落库

### D. 数据分析
必需能力：
- 可按“用户/场景/时间段/多用户对比”等维度查询数据
- 触发分析模型进行长上下文处理（可能涉及模型切换/重新加载）
- 结构化 + 非结构化输出
- 关键分析结果落库，并生成可视化数据源（前端暂不动，但要保证数据可被图表渲染）

## 推荐技术栈（按“稳定、开发容易、debug方便、少自研”原则）

### 后端核心
- Python 3.11+
- FastAPI（REST + WebSocket）
- pydantic-settings（配置）
- SQLModel + SQLAlchemy 2.0（ORM）
- Alembic（数据库迁移/版本化）
- httpx（调用 LM Studio/OpenAI兼容接口、内部服务调用）

### LLM 接入与路由
- 直接用 openai-python（指向 LM Studio OpenAI兼容 base_url）
  - 优点：最少依赖、最容易 debug
- 可选：LiteLLM（当你需要切换更多提供方/做统一计费与路由时再引入）

### Prompt 管理
- P0：Jinja2 模板 + Git 版本控制（模板存放在仓库 prompts/）
  - 优点：可 code review、可回滚、无额外平台依赖
- P1：Langfuse 或 PromptLayer（做 prompt registry、版本、A/B、回放）

### 实时通信与状态同步（多模态“多态”核心）
- WebSocket（FastAPI 原生支持）
- 统一事件协议（建议强制）：
  - event: type（例如 OCR_PROGRESS/LLM_TOKEN/TTS_CHUNK/FINAL）
  - seq: 递增序列号
  - conversation_id/session_id
  - idempotency_key（可选）
  - payload（与 type 对应的 JSON）
- 断线恢复：客户端携带 last_seq，服务端可重放（依赖“会话事件日志”）

### OCR / ASR / TTS
- OCR：PaddleOCR（保持你现有方向；稳定但依赖重）
- ASR：faster-whisper（本地推理） + webrtcvad（判停）
- TTS：XTTS（保持现有方向）
- 音频处理：优先使用 soundfile/librosa；pydub 作为格式转换兜底

### 缓存与临时数据
- diskcache（本地落盘缓存，简单可靠）
- 临时文件目录统一管理 + 清理策略（TTL）

### 后台任务（按需引入）
- P0：进程内任务 + asyncio task group（短任务）
- P1：RQ（Redis Queue）或 Dramatiq + Redis（长任务、重试、隔离 worker）
  - 说明：在 Windows/桌面本地场景，Redis 是额外依赖；必须等出现明确需求再上

### 日志/可观测/调试
- structlog（结构化日志）
- OpenTelemetry（可选，P1）
- 会话事件日志（强烈建议 P0）：
  - 将所有关键事件 append-only 写入用户库/或独立表，支持回放与定位 bug

## 数据存储策略（按需求落地版）

你提出：公共数据 PostgreSQL、用户数据 SQLite。我建议分阶段实现：

- P0（先跑通、少运维）：公共词库也用 SQLite + FTS5（或打包只读词库文件）
  - 理由：桌面/本地部署更稳，不引入 PostgreSQL 安装与运维负担
- P1（如确需全文检索/多用户共享/服务器部署）：公共词库迁到 PostgreSQL
  - 使用 pg_trgm / full-text search

用户数据：
- SQLite（单库分表 + user_id）或“每用户一个 SQLite 文件”二选一
  - P0 推荐：单库分表（实现简单，便于统计）
  - P1 可选：每用户一库（隐私隔离更强，但管理复杂度更高）

## 里程碑（M0~M6）

### M0：冻结协议与验收用例（必须先做）
交付物：
- OpenAPI 草案（REST）+ WebSocket 事件协议文档（type 列表 + payload schema）
- 端到端验收用例清单（可自动化）
- 数据库 schema 草案（公共词库/用户库/会话事件日志表）

验收标准：
- 用例可被自动化脚本驱动（即使功能未实现，也要能跑到“expected fail”并定位）

#### WS 事件协议（P0 强制）

目的：
- 让“文字/图片/语音”等不同输入模态共享同一会话上下文（多态），并能流式推送中间态。
- 让 debug 从“猜”变成“可回放”：任何一次失败都能通过事件日志复现。

连接与身份：
- 建议路径：`/ws/v1?session_id=...&user_id=...`（最终以 OpenAPI/路由实现为准）
- P0：沿用现有鉴权方式（前端不改）
- P1：切到标准 Bearer Token（或 fastapi-users）

通用字段（所有事件必须包含）：
- `type`：事件类型（字符串，见下）
- `seq`：严格递增的序列号（uint64，连接内单调递增）
- `ts`：服务端生成时间戳（毫秒）
- `session_id`：会话 ID（字符串）
- `conversation_id`：对话/任务 ID（字符串；同一会话下可并行多个任务时用来区分）
- `request_id`：一次用户触发动作的请求 ID（字符串，用于日志/追踪）
- `payload`：与事件类型对应的 JSON 对象

可选字段（用于鲁棒性与调试）：
- `trace_id`：链路追踪 ID（P1）
- `idempotency_key`：幂等键（客户端生成；用于避免重连重复提交）
- `final`：布尔值；标记该 `conversation_id` 是否结束（仅对部分事件适用）

重连与恢复（P0 强制）：
- 客户端断线后重连时携带：`last_seq`（上一次收到的最大 seq）
- 服务端行为：
  - 若存在事件日志：从 `last_seq + 1` 开始重放，直到最新
  - 若不存在：至少发送 `ERROR` 事件说明无法恢复（并建议客户端重新开始任务）

事件类型（P0 最小集合）：
- `PING` / `PONG`：心跳
- `ERROR`：错误事件（见错误码）
- `TASK_STARTED`：开始处理（例如 OCR/LLM/ASR/TTS）
- `OCR_PROGRESS`：OCR 进度/阶段信息
- `OCR_RESULT`：OCR 最终文本
- `LLM_TOKEN`：LLM 流式 token（P1，可选；P0 可不实现）
- `LLM_RESULT`：LLM 最终 Markdown
- `TTS_CHUNK`：TTS 音频分片（P1；P0 可先用 `TTS_RESULT`）
- `TTS_RESULT`：TTS 最终音频（Base64 或文件引用）
- `ASR_PARTIAL`：ASR 中间文本（P1）
- `ASR_FINAL`：ASR 最终文本
- `ANALYSIS_RESULT`：结构化分析结果（作文批改/数据分析）
- `TASK_FINISHED`：任务结束（final=true）

（P1 推荐补充）：
- `TASK_ABORTED`：任务被取消/打断（例如用户 Barge-in 触发取消 LLM/TTS）

错误码（P0 最小集合）：
- `VALIDATION_ERROR`：入参缺失/格式不对
- `AUTH_REQUIRED`：鉴权失败
- `RATE_LIMITED`：限流
- `SERVICE_UNAVAILABLE`：外部依赖不可用（LM Studio/OCR/ASR/TTS）
- `TIMEOUT`：超时
- `MODEL_OUTPUT_INVALID`：模型输出无法解析/不符合 schema
- `RECOVERY_NOT_SUPPORTED`：无法重放（无事件日志/过期）

示例（LLM_RESULT）：
```json
{
  "type": "LLM_RESULT",
  "seq": 42,
  "ts": 1735060000000,
  "session_id": "u_12",
  "conversation_id": "vocab_20251225_001",
  "request_id": "req_abc",
  "payload": {
    "format": "markdown",
    "word": "example",
    "markdown": "# example\n..."
  }
}
```

#### 端到端验收用例（P0 必须自动化）

说明：所有用例都要产出可断言的“结构化外壳”（即使内部文本不完全一致）。

词汇查询：
- `vocab_text_hit`：公共库命中 -> 不调用 LLM -> 推送 `TASK_STARTED` + `LLM_RESULT`（来自库）+ `TASK_FINISHED`
- `vocab_text_miss_then_generate`：公共库未命中 -> 调用 LLM -> 写回公共库 -> 写用户查询历史
- `vocab_image_ocr_then_query`：OCR->文本->查词链路；至少推送 `OCR_RESULT` 与 `LLM_RESULT`

作文批改：
- `essay_image_ocr_then_analyze`：OCR->分析模型->结构化 JSON；断言 `ANALYSIS_RESULT.payload` 含 score/feedback/suggestions（字段名以最终 schema 为准）

语音对话：
- `voice_prompt_expand`：输入 scenario/language -> 返回 system prompt（可走 WS 或 HTTP）
- `voice_audio_single_turn_non_streaming`（P0）：音频分片上传 -> `ASR_FINAL` -> `LLM_RESULT` -> `TTS_RESULT`

（P1：全双工优先验收用例）
- `voice_audio_single_turn_llm_stream`：`ASR_FINAL` 后推送多个 `LLM_TOKEN`，最后 `LLM_RESULT`
- `voice_audio_single_turn_tts_chunk`：收到 `TTS_CHUNK` 序列，且可选仍返回 `TTS_RESULT` 兼容旧前端
- `voice_barge_in_interrupts_output`：系统开始输出（LLM/TTS）后，用户再次开始说话 -> 服务端推送 `TASK_ABORTED`，并停止旧任务后续 `LLM_TOKEN/TTS_CHUNK`

数据分析：
- `analysis_trigger_and_persist`：触发分析 -> 返回结构化结果 -> 结果落库可查询

#### DB Schema 草案（P0 先以 SQLite 为主）

原则：
- 所有“可回放/可 debug”的核心信息都要落到事件日志表（append-only）。
- 公共词库与用户数据可先同为 SQLite，不阻碍后续把公共词库迁到 PostgreSQL。

建议表（名称可调整）：
- `public_vocab_entries`（公共库）
  - `id`, `term`, `language`, `markdown`, `source`(model/db), `created_at`, `updated_at`
  - 索引：`term`, `language`；P0 使用 FTS5（`term + markdown`）
- `user_vocab_queries`（用户查询历史）
  - `id`, `user_id`, `term`, `source`(text/ocr/voice), `timestamp`, `public_entry_id`(nullable)
- `essay_submissions`
  - `id`, `user_id`, `image_ref`(path/blob), `ocr_text`, `created_at`
- `essay_results`
  - `id`, `submission_id`, `result_json`, `score`, `created_at`
- `conversations`
  - `id`, `user_id`, `scenario`, `language`, `system_prompt`, `started_at`, `ended_at`
- `conversation_events`（会话事件日志，append-only，重放依赖它）
  - `id`, `session_id`, `conversation_id`, `seq`, `type`, `payload_json`, `ts`, `request_id`
  - 索引：`(session_id, conversation_id, seq)` 唯一；按 `ts` 查询

TODO：
- [ ] 定义 WS 事件协议（含 seq、重连恢复、错误码）
- [ ] 定义 4 个场景的最小验收输入/输出
- [ ] 定义 DB 表结构与迁移策略（Alembic）

### M1：FastAPI 基座 + 工程化
交付物：
- FastAPI 项目骨架（分层：api/routes、domain、services、adapters、db、prompts）
- 配置管理（pydantic-settings）
- 统一错误码与异常处理
- 结构化日志（structlog）
- pytest 基础测试框架（httpx + websocket 测试）

TODO：
- [ ] 初始化 Python 项目与依赖锁定
- [ ] 实现 health/config endpoints
- [ ] 实现 WebSocket 基础连接与事件发送

### M2：单词查询（文字/图片）闭环
交付物：
- 文本查词：命中公共库直接返回；未命中调用 LLM 生成 Markdown 并写回公共库
- 图片查词：OCR -> 文本查词
- WS 推送：支持 progress + final（至少 2 类事件）
- 用户库记录查询历史

TODO：
- [ ] 公共词库最小实现（P0 先 SQLite FTS5）
- [ ] LM Studio OpenAI 兼容调用封装（含超时/重试/日志）
- [ ] OCR 适配器（输入 base64/文件）
- [ ] WS 推送协议落地（OCR_PROGRESS / LLM_FINAL）
- [ ] 契约测试：固定输入 -> 固定输出结构

### M3：作文批改闭环
交付物：
- OCR -> 分析模型 -> 结构化 JSON -> 用户库持久化
- WS/HTTP 返回（根据前端现状选择：若已用 WS，则推送；否则 HTTP 返回）

TODO：
- [ ] 作文批改 prompt 模板（Jinja2）
- [ ] 分析模型调用（json schema 校验 + 容错）
- [ ] 用户库表：essay_submissions / essay_results
- [ ] 回放能力：能重放一次批改全流程

### M4：语音对话（先可用、后低延迟）
交付物（阶段 1：可用）：
- WS 双向：音频分片上传、ASR 文本回推、最终回复文本回推、最终 TTS 音频回推
- VAD/停顿判定：能可靠判断一句话结束

交付物（阶段 2：全双工（可打断）+ 低延迟流式）：
- LLM token 流式事件（`LLM_TOKEN`），并保证可取消
- TTS 分片流式事件（`TTS_CHUNK`），并保证可取消
- Barge-in：用户开始说话时，取消当前 LLM/TTS 并停止继续推送（`TASK_ABORTED`）

TODO：
- [ ] 定义音频分片格式（pcm/opus/wav）与采样率
- [ ] faster-whisper + VAD 适配
- [ ] LLM 流式输出协议（LLM_TOKEN）
- [ ] TTS 分片协议（TTS_CHUNK）
- [ ] Barge-in 取消协议与幂等语义（TASK_ABORTED）
- [ ] 对话结束分析（分析模型）+ 用户库落库

### M5：数据分析能力
交付物：
- 分析任务 API：按维度选择数据源（用户/场景/时间段/多用户）
- 结构化结果落库 + 可视化数据源输出
- 支持“长上下文”处理（必要时模型切换/加载）

TODO：
- [ ] 数据查询层（可复用 repository）
- [ ] 分析 prompt 模板与 schema
- [ ] 任务执行策略（必要时引入队列 P1）

### M6：稳定性与回归体系（替代“看似正常”）
交付物：
- 契约测试 + 集成测试覆盖 4 个场景
- 失败可定位：trace_id + 会话事件回放
- 性能与资源基线（CPU/内存/首 token 延迟/端到端延迟）

TODO：
- [ ] 构建测试数据集与金标输出（snapshot）
- [ ] 加入失败重试与熔断策略（LLM/OCR/ASR/TTS）
- [ ] 加入缓存策略（diskcache）

## 风险与对策（简表）
- Windows 本地环境依赖复杂（ASR/TTS/OCR）：先做“可用”闭环，再做加速；并强制用 env_check 脚本做环境探测。
- 模型输出不稳定：必须用 schema 校验 + 容错解析 + 回退展示（Markdown 兜底）。
- WS 状态错乱：必须统一事件协议 + seq + 会话事件日志，支持回放与断线恢复。

## P0 / P1 / P2 优先级
- P0：M0-M3（查词/作文先闭环）+ 事件协议 + 回放
- P1：M4（语音流式低延迟）+ 队列 + 可观测增强
- P2：Prompt 平台化（Langfuse/PromptLayer）、评测体系、A/B
