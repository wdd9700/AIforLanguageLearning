# Phase 4 核心功能交接文档 — 对话模块（Dialogue）

**交接日期**: 2026年4月12日  
**负责成员**: 成员 C（对话模块）  
**前置条件**: Phase 3 基础设施加固已完成，测试全绿（`pytest tests/ -m "not integration"` = 97 passed）

---

## 1. 工作范围

负责实现以下核心能力：
1. **场景扩写引擎** — 将用户简单场景描述扩展为结构化对话设定（Prompt Engineering）
2. **对话会话管理** — 创建对话、维护上下文、存储对话历史
3. **WebSocket 语音对话链路** — ASR → LLM → TTS 完整实时链路
4. **对话结束与反馈** — 总结学习表现、生成能力报告

---

## 2. 当前基座状态（已就绪，可直接使用）

### 2.1 数据模型
- **文件**: `backend_fastapi/app/models.py`
- **相关模型**:
  - `ConversationEvent` — 对话事件表（`session_id`, `conversation_id`, `seq`, `type`, `payload` JSON）
  - `UserVocabQuery` — 用户查词历史（可复用记录对话中的查词行为）

### 2.2 基础设施封装
- **LLM 服务** — `backend_fastapi/app/llm.py`
  - `chat_complete()` — 通用对话补全
  - `stream_chat()` — 流式对话输出
  - `generate_definition()` — 生成定义/解释
- **TTS 服务** — `backend_fastapi/app/tts.py`
  - `synthesize_tts_wav()` — 合成语音 WAV
- **语音流/ASR** — `backend_fastapi/app/voice_stream.py`
  - `VoiceStream` / `VoiceStreamConfig`
  - `try_create_faster_whisper_transcriber()` / `try_create_openai_whisper_transcriber()`
- **WebSocket 路由** — `backend_fastapi/app/routers/voice.py`
  - 已有 `/ws/v1` WebSocket 端点，支持 AUDIO_START / AUDIO_CHUNK / AUDIO_STOP 等消息类型
- **上下文存储** — `backend_fastapi/app/context_store.py`
  - 已封装对话上下文管理

### 2.3 现有路由
- `backend_fastapi/app/routers/voice.py` — WebSocket 语音对话路由
- `backend_fastapi/app/routers/learning.py` — 学习相关路由，可扩展对话历史查询
- `backend_fastapi/app/main.py` — WebSocket 端点已注册

---

## 3. 需要完成的工作

### 3.1 场景扩写引擎
**文件建议**: `backend_fastapi/app/domain/dialogue/scene_engine.py`

**实现要求**:
1. 接收用户简单场景输入（如 `"我想练习餐厅点餐"`）
2. 构建结构化 Prompt，调用 `llm.chat_complete()` 扩写为完整场景设定
3. 输出严格的 JSON 格式，包含以下字段：
   - `scene_name` — 场景名称
   - `setting` — 背景设定（location, time, roles, atmosphere）
   - `learning_objectives` — 学习目标列表
   - `key_vocabulary` — 核心词汇列表
   - `difficulty_level` — 难度等级
   - `estimated_duration` — 预计时长
   - `opening_line` — AI 开场白

**Prompt 模板示例**:
```
你是一个专业的英语对话场景设计专家。
请将用户的简单场景描述扩展为详细的对话设定。

输入场景: {user_input}
用户水平: {user_level}

请输出严格 JSON 格式：
{
  "scene_name": "...",
  "setting": {...},
  "learning_objectives": [...],
  "key_vocabulary": [...],
  "difficulty_level": "...",
  "estimated_duration": "...",
  "opening_line": "..."
}
```

### 3.2 对话会话管理 API
**路由建议**:
- `POST /api/v1/dialogues/start` — 创建新对话会话
- `GET /api/v1/dialogues/{conversation_id}` — 查询对话历史
- `POST /api/v1/dialogues/{conversation_id}/end` — 结束对话，生成反馈

**实现要求**:
1. `POST /start`:
   - 接收 `scene` 参数（用户场景描述）
   - 调用场景扩写引擎生成结构化设定
   - 创建 `conversation_id`（UUID）
   - 将 `scene_setting` 和 `opening_line` 写入 `ConversationEvent`（type=`SCENE_SET`）
   - 返回会话信息和开场白

2. `GET /{conversation_id}`:
   - 按 `seq` 顺序查询该会话的所有 `ConversationEvent`
   - 返回完整对话历史

3. `POST /{conversation_id}/end`:
   - 标记对话结束
   - 调用 LLM 分析整个对话历史，生成学习反馈
   - 返回反馈报告（包含表现评分、错误纠正、建议）

**接口契约**:
```json
// POST /api/v1/dialogues/start Request
{
  "scene": "我想练习餐厅点餐",
  "language": "en"
}

// Response
{
  "success": true,
  "data": {
    "conversation_id": "conv-uuid-123",
    "scene_setting": {
      "scene_name": "餐厅点餐",
      "setting": {...},
      "learning_objectives": [...],
      "key_vocabulary": ["appetizer", "entree", "beverage"],
      "difficulty_level": "intermediate",
      "opening_line": "Hi, welcome to our restaurant! ..."
    }
  }
}

// GET /api/v1/dialogues/{id} Response
{
  "success": true,
  "data": {
    "conversation_id": "conv-uuid-123",
    "events": [
      {"seq": 1, "type": "SCENE_SET", "payload": {...}},
      {"seq": 2, "type": "AI_MESSAGE", "payload": {"text": "Hi, welcome..."}},
      {"seq": 3, "type": "USER_MESSAGE", "payload": {"text": "I'd like a table for two."}},
      {"seq": 4, "type": "AI_MESSAGE", "payload": {"text": "Sure, right this way..."}}
    ]
  }
}

// POST /api/v1/dialogues/{id}/end Response
{
  "success": true,
  "data": {
    "conversation_id": "conv-uuid-123",
    "feedback": {
      "overall_score": 85,
      "strengths": ["发音清晰", "用词准确"],
      "weaknesses": ["时态使用不够稳定"],
      "suggestions": ["多练习过去时态表达"],
      "key_vocabulary_mastery": {...}
    }
  }
}
```

### 3.3 WebSocket 语音对话链路优化
**文件**: `backend_fastapi/app/routers/voice.py` 和 `backend_fastapi/app/voice_stream.py`

**当前状态**:
- `/ws/v1` 已存在，支持音频流的上传和 ASR 识别
- 但 LLM 回复生成和 TTS 语音输出可能未完全闭环

**实现要求**:
1. 确保 WebSocket 消息流完整闭环：
   ```
   用户语音输入
       │
       ▼
   ┌─────────────────┐
   │  ASR 识别        │  voice_stream.py / faster-whisper
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │  构建 LLM Prompt │  注入场景设定 + 对话历史
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │  LLM 生成回复    │  llm.chat_complete() / stream_chat()
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │  TTS 语音合成    │  tts.synthesize_tts_wav()
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │  WebSocket 返回  │  音频流 + 文本
   └─────────────────┘
   ```
2. 每轮对话将 `USER_MESSAGE` 和 `AI_MESSAGE` 写入 `ConversationEvent`
3. 支持流式返回：先返回文本，再返回合成音频（或音频 URL）
4. 错误处理：ASR 失败时返回友好提示，不中断 WebSocket 连接

**消息类型约定**:
- `AUDIO_START` / `AUDIO_CHUNK` / `AUDIO_STOP` — 音频输入控制
- `ASR_PARTIAL` / `ASR_FINAL` — ASR 中间结果/最终结果
- `AI_TEXT` — LLM 文本回复
- `AI_AUDIO` — TTS 音频数据（base64 或 URL）
- `ERROR` — 错误提示

### 3.4 动态难度调整
**实现要求**:
1. 根据 `StudentProfile.level`（`beginner` / `intermediate` / `advanced`）调整 LLM Prompt：
   - `beginner`: 简单句、基础词汇、慢语速（TTS 语速参数）
   - `intermediate`: 复合句、常用表达、正常语速
   - `advanced`: 复杂句、地道表达、自然语速
2. 在场景扩写 Prompt 中注入用户水平信息

---

## 4. 依赖关系

| 依赖模块 | 状态 | 说明 |
|----------|------|------|
| LLM 调用 | ✅ 就绪 | `llm.py` 已封装 Kimi API |
| TTS 合成 | ✅ 就绪 | `tts.py` 已封装 |
| ASR/语音流 | ✅ 就绪 | `voice_stream.py` 已封装 |
| WebSocket | ✅ 就绪 | `routers/voice.py` 已有基础路由 |
| 对话事件存储 | ✅ 就绪 | `models.py` 中 `ConversationEvent` 已定义 |
| 上下文存储 | ✅ 就绪 | `context_store.py` 已封装 |

---

## 5. 验收标准

- [ ] `POST /api/v1/dialogues/start` 能根据用户场景输入返回结构化场景设定和开场白
- [ ] 场景扩写输出为合法 JSON，包含所有必需字段
- [ ] WebSocket `/ws/v1` 支持完整的 ASR → LLM → TTS 闭环对话
- [ ] 每轮对话的 `USER_MESSAGE` 和 `AI_MESSAGE` 正确写入 `ConversationEvent`
- [ ] `GET /api/v1/dialogues/{id}` 能按顺序返回完整对话历史
- [ ] `POST /api/v1/dialogues/{id}/end` 能生成学习反馈报告
- [ ] 对话难度根据用户 `StudentProfile.level` 动态调整
- [ ] 新增测试文件 `tests/test_dialogue_module.py`，覆盖场景扩写、历史查询、WebSocket 基础消息流
- [ ] `pytest tests/ -m "not integration"` 仍然全绿

---

## 6. 注意事项与风险

1. **LLM JSON 输出稳定性**: 场景扩写要求严格 JSON 输出，但 LLM 偶尔会在 JSON 外包裹 markdown 代码块。建议做后处理：提取 ```json ... ``` 中的内容，或设置 `response_format={"type": "json_object"}`（若模型支持）。
2. **WebSocket 长连接稳定性**: 语音对话可能持续数分钟，需确保连接不会因超时断开。检查 `voice_stream.py` 中的超时配置。
3. **ASR 模型加载**: `faster-whisper` 模型首次加载较慢（数秒），建议在应用启动时预热加载，或在前端显示 "准备中" 提示。
4. **TTS 流式输出**: 当前 `tts.synthesize_tts_wav()` 可能返回完整 WAV 文件，大段文本时延迟较高。可先按句子切分，逐句合成返回，后续再优化为真正的流式 TTS。
5. **对话历史长度控制**: 长对话时历史消息可能超出 LLM 上下文窗口。建议只保留最近 N 轮（如 10 轮）作为上下文，更早的做摘要压缩。
6. **并发会话隔离**: 确保不同 `conversation_id` 的对话事件不互相干扰，`session_id` 和 `conversation_id` 组合唯一标识会话。

---

## 7. 参考文档

- `docs/Detailed_System_Architecture.md` 第 3 章（对话模块详细架构）
- `backend_fastapi/app/llm.py`
- `backend_fastapi/app/tts.py`
- `backend_fastapi/app/voice_stream.py`
- `backend_fastapi/app/routers/voice.py`
- `backend_fastapi/app/models.py`（`ConversationEvent`）
- `backend_fastapi/app/context_store.py`
