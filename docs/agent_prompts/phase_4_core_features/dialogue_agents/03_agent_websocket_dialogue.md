# Agent: WebSocket语音对话链路开发者 (WebSocket Dialogue Developer)

## 角色定位
你是**WebSocket语音对话链路**的专项开发Agent，负责优化ASR → LLM → TTS的实时闭环对话体验。

## 使用时机
- 需要优化WebSocket语音对话流程时
- 需要实现对话事件持久化时
- 需要处理打断和上下文续接时

---

## 任务范围

### 核心职责
1. 优化 `backend_fastapi/app/main.py` 中的 `/ws/v1` 处理逻辑
2. 确保每轮对话事件正确写入 `ConversationEvent`
3. 集成场景设定到对话上下文
4. 优化流式响应体验

### 当前状态分析

**已实现的优秀基础:**
- ✅ WebSocket连接管理
- ✅ ASR流式识别（Partial/Final）
- ✅ LLM流式生成（Token级）
- ✅ TTS分块返回
- ✅ Barge-in打断支持
- ✅ 打断上下文续接
- ✅ 重连恢复机制

**需要补充的工作:**
- ❌ 场景设定注入到System Prompt
- ❌ USER_MESSAGE/AI_MESSAGE事件持久化
- ❌ 对话难度动态调整
- ❌ 场景特定词汇高亮

---

## 消息流架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     WebSocket /ws/v1                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  用户语音输入                                                    │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────────┐     AUDIO_START/CHUNK/STOP                 │
│  │  VoiceStream    │ ◄── 音频流缓冲                              │
│  │  (已存在)        │                                            │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐     ASR_PARTIAL / ASR_FINAL                 │
│  │  ASR识别         │ ──► 发送识别结果                            │
│  │  faster-whisper │                                            │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐     构建LLM Prompt                          │
│  │  上下文组装      │ ◄── 注入场景设定 + 对话历史                   │
│  │  (需实现)        │                                            │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐     LLM_TOKEN / LLM_RESULT                  │
│  │  LLM生成         │ ──► 流式返回文本                            │
│  │  stream_chat()  │                                            │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐     TTS_CHUNK / TTS_RESULT                  │
│  │  TTS合成         │ ──► 流式返回音频                            │
│  │  synthesize_tts │                                            │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐     USER_MESSAGE / AI_MESSAGE               │
│  │  事件持久化      │ ──► 写入ConversationEvent                   │
│  │  (需实现)        │                                            │
│  └─────────────────┘                                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 关键修改点

### 1. 场景设定注入

在WebSocket连接初始化时，读取场景设定并构建System Prompt:

```python
async def ws_v1(ws: WebSocket) -> None:
    # ... 现有代码 ...
    
    # 新增：获取场景设定
    scene_setting = await get_scene_setting(conversation_id)
    if scene_setting:
        system_prompt = build_dialogue_system_prompt(scene_setting)
    else:
        system_prompt = get_latest_system_prompt()
    
    # 新增：根据用户水平调整
    user_level = await get_user_level(session_id)
    system_prompt = apply_difficulty_adjustment(system_prompt, user_level)
```

### 2. 对话事件持久化

在ASR_FINAL和LLM_RESULT时写入事件:

```python
# ASR识别完成后
await send_event("ASR_FINAL", {"text": final_text}, ...)
# 新增：同时写入USER_MESSAGE
await store_dialogue_event(
    conversation_id=conversation_id,
    type="USER_MESSAGE",
    payload={"text": final_text, "source": "asr"}
)

# LLM生成完成后
await send_event("LLM_RESULT", {"text": full_text, ...}, ...)
# 新增：同时写入AI_MESSAGE
await store_dialogue_event(
    conversation_id=conversation_id,
    type="AI_MESSAGE",
    payload={"text": full_text, "audio_duration": audio_duration}
)
```

### 3. 动态难度调整

```python
def apply_difficulty_adjustment(system_prompt: str, user_level: str) -> str:
    """根据用户水平调整System Prompt"""
    adjustments = {
        "beginner": {
            "vocabulary": "使用基础词汇，避免生僻词",
            "sentence": "使用简单句，避免复杂从句",
            "pace": "语速放慢，给用户思考时间",
            "support": "必要时提供中文提示",
            "correction": "温和纠正错误，先肯定后建议"
        },
        "intermediate": {
            "vocabulary": "使用常用表达，适度引入新词汇",
            "sentence": "使用复合句，保持自然流畅",
            "pace": "正常语速",
            "support": "鼓励完整表达",
            "correction": "指出错误并给出正确表达"
        },
        "advanced": {
            "vocabulary": "使用地道习语和高级表达",
            "sentence": "使用复杂句，展现语言丰富性",
            "pace": "自然语速，包括停顿和强调",
            "support": "深入讨论话题",
            "correction": "指出细微错误，追求精确表达"
        }
    }
    
    adjustment = adjustments.get(user_level, adjustments["intermediate"])
    return f"""{system_prompt}

【难度调整】
- 词汇要求: {adjustment['vocabulary']}
- 句子结构: {adjustment['sentence']}
- 语速控制: {adjustment['pace']}
- 辅助策略: {adjustment['support']}
- 纠错方式: {adjustment['correction']}
"""
```

---

## 技术规范

### 新增事件类型

| 事件类型 | 说明 | 来源 |
|---------|------|------|
| `SCENE_SET` | 场景设定 | dialogue.py |
| `USER_MESSAGE` | 用户消息 | WebSocket |
| `AI_MESSAGE` | AI回复 | WebSocket |
| `DIALOGUE_ENDED` | 对话结束 | dialogue.py |

### 修改文件

```
backend_fastapi/app/main.py
    ├── ws_v1() 函数优化
    ├── 新增 get_scene_setting()
    ├── 新增 build_dialogue_system_prompt()
    ├── 新增 store_dialogue_event()
    └── 新增 apply_difficulty_adjustment()

backend_fastapi/app/domain/dialogue/
    ├── context_builder.py     # 上下文构建器（新增）
    └── difficulty.py          # 难度调整（新增）
```

---

## 实现要点

### 1. 上下文构建器

```python
class DialogueContextBuilder:
    """构建LLM对话上下文"""
    
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
    
    async def build_system_prompt(self) -> str:
        """构建System Prompt"""
        scene = await self._get_scene_setting()
        history = await self._get_recent_history(limit=5)
        
        return f"""你是{scene.setting['roles'][0]}，正在{scene.setting['location']}与用户进行英语对话练习。

场景: {scene.scene_name}
背景: {scene.setting['atmosphere']}
学习目标: {', '.join(scene.learning_objectives)}
核心词汇: {', '.join(scene.key_vocabulary)}

对话历史:
{self._format_history(history)}

请保持角色扮演，帮助用户完成学习目标。如果用户表达有误，请温和地纠正。
"""
    
    def _format_history(self, messages: list[dict]) -> str:
        """格式化历史消息"""
        ...
```

### 2. 事件存储优化

```python
async def store_dialogue_event(
    conversation_id: str,
    type: str,
    payload: dict,
    *,
    db_session: Session | None = None
) -> None:
    """存储对话事件"""
    event = ConversationEvent(
        conversation_id=conversation_id,
        type=type,
        payload=payload,
        seq=await get_next_seq(conversation_id),
        ts=int(time.time() * 1000)
    )
    
    if db_session:
        db_session.add(event)
    else:
        with Session(get_engine()) as session:
            session.add(event)
            session.commit()
```

---

## 验收标准

- [ ] WebSocket对话能正确注入场景设定
- [ ] 每轮USER_MESSAGE正确写入ConversationEvent
- [ ] 每轮AI_MESSAGE正确写入ConversationEvent
- [ ] 对话难度根据用户水平动态调整
- [ ] 打断后上下文能正确续接
- [ ] 重连后能正确恢复对话状态
- [ ] 流式响应延迟 < 500ms
- [ ] 集成测试验证完整链路

---

## 依赖关系

```
WebSocket优化
    ├── app.domain.dialogue.scene_engine (Agent 01)
    ├── app.domain.dialogue.context_builder (本Agent)
    ├── app.domain.dialogue.difficulty (本Agent)
    ├── app.models.ConversationEvent (已就绪)
    ├── app.llm.stream_chat (已就绪)
    ├── app.tts.synthesize_tts_wav (已就绪)
    └── app.voice_stream.VoiceStream (已就绪)
```

## 注意事项

1. **性能优化**: 场景设定应缓存，避免每轮查询
2. **并发处理**: 事件写入需处理并发seq分配
3. **错误恢复**: ASR/LLM/TTS失败时保持连接
4. **内存管理**: 长对话需控制上下文长度
5. **向后兼容**: 不破坏现有WebSocket协议
