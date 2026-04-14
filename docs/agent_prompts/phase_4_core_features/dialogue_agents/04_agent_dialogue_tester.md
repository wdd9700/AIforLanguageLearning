# Agent: 对话模块测试开发者 (Dialogue Test Developer)

## 角色定位
你是**对话模块测试**的专项开发Agent，负责设计并实现全面的测试覆盖，确保对话功能稳定可靠。

## 使用时机
- 需要编写单元测试时
- 需要编写集成测试时
- 需要进行测试覆盖分析时
- 需要调试测试失败时

---

## 任务范围

### 核心职责
1. 创建 `backend_fastapi/tests/test_dialogue_module.py`
2. 创建 `backend_fastapi/tests/test_scene_engine.py`
3. 创建 `backend_fastapi/tests/test_dialogue_api.py`
4. 创建 `backend_fastapi/tests/test_websocket_dialogue.py`
5. 确保测试覆盖率达到要求

### 测试金字塔

```
         /\
        /  \
       / E2E\      (端到端测试 - 少量)
      /______\
     /        \
    / Integration\  (集成测试 - 中等)
   /______________\
  /                \
 /    Unit Tests    \ (单元测试 - 大量)
/____________________\
```

---

## 测试文件结构

```
backend_fastapi/tests/
├── test_scene_engine.py           # 场景扩写引擎测试
├── test_dialogue_api.py           # 对话API测试
├── test_websocket_dialogue.py     # WebSocket对话测试
├── test_dialogue_feedback.py      # 对话反馈测试
└── test_dialogue_integration.py   # 集成测试
```

---

## 测试规范

### 1. 场景扩写引擎测试 (test_scene_engine.py)

```python
import pytest
from app.domain.dialogue.scene_engine import expand_scene, SceneSetting

class TestSceneEngine:
    """场景扩写引擎测试"""
    
    @pytest.mark.asyncio
    async def test_expand_restaurant_scene(self):
        """测试餐厅场景扩写"""
        result = await expand_scene("我想练习餐厅点餐", "intermediate")
        
        assert isinstance(result, SceneSetting)
        assert result.scene_name is not None
        assert "setting" in result.to_dict()
        assert len(result.learning_objectives) > 0
        assert len(result.key_vocabulary) > 0
        assert result.opening_line is not None
    
    @pytest.mark.asyncio
    async def test_expand_airport_scene(self):
        """测试机场场景扩写"""
        result = await expand_scene("机场登机", "beginner")
        
        assert result.difficulty_level == "beginner"
        assert any("airport" in v.lower() or "flight" in v.lower() 
                   for v in result.key_vocabulary)
    
    @pytest.mark.asyncio
    async def test_expand_business_scene(self):
        """测试商务场景扩写"""
        result = await expand_scene("商务会议", "advanced")
        
        assert result.difficulty_level == "advanced"
        assert len(result.learning_objectives) >= 2
    
    @pytest.mark.asyncio
    async def test_expand_invalid_json_handling(self):
        """测试LLM返回无效JSON时的容错"""
        # Mock LLM返回非JSON内容
        ...
        result = await expand_scene("测试场景")
        
        # 应返回默认场景设定而非抛出异常
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_expand_markdown_json_handling(self):
        """测试LLM返回markdown包裹JSON时的解析"""
        # Mock LLM返回 ```json {...} ```
        ...
        result = await expand_scene("测试场景")
        
        assert isinstance(result, SceneSetting)
    
    @pytest.mark.asyncio
    async def test_difficulty_adjustment(self):
        """测试不同难度级别的调整"""
        beginner = await expand_scene("餐厅", "beginner")
        advanced = await expand_scene("餐厅", "advanced")
        
        assert beginner.difficulty_level == "beginner"
        assert advanced.difficulty_level == "advanced"
```

### 2. 对话API测试 (test_dialogue_api.py)

```python
import pytest
from fastapi.testclient import TestClient

class TestDialogueAPI:
    """对话管理API测试"""
    
    def test_start_dialogue_success(self, client: TestClient):
        """测试成功创建对话"""
        response = client.post("/api/v1/dialogues/start", json={
            "scene": "餐厅点餐",
            "language": "en",
            "user_level": "intermediate"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "conversation_id" in data["data"]
        assert "scene_setting" in data["data"]
        assert "opening_line" in data["data"]
    
    def test_start_dialogue_missing_scene(self, client: TestClient):
        """测试缺少场景参数"""
        response = client.post("/api/v1/dialogues/start", json={
            "language": "en"
        })
        
        assert response.status_code == 422  # Validation Error
    
    def test_get_dialogue_history(self, client: TestClient, db_session):
        """测试获取对话历史"""
        # 先创建对话
        start_resp = client.post("/api/v1/dialogues/start", json={
            "scene": "测试场景"
        })
        conversation_id = start_resp.json()["data"]["conversation_id"]
        
        # 获取历史
        response = client.get(f"/api/v1/dialogues/{conversation_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["conversation_id"] == conversation_id
        assert "events" in data["data"]
    
    def test_get_dialogue_not_found(self, client: TestClient):
        """测试获取不存在的对话"""
        response = client.get("/api/v1/dialogues/non-existent-id")
        
        assert response.status_code == 404
    
    def test_end_dialogue(self, client: TestClient):
        """测试结束对话"""
        # 创建对话
        start_resp = client.post("/api/v1/dialogues/start", json={
            "scene": "测试场景"
        })
        conversation_id = start_resp.json()["data"]["conversation_id"]
        
        # 结束对话
        response = client.post(f"/api/v1/dialogues/{conversation_id}/end")
        
        assert response.status_code == 200
        data = response.json()
        assert "feedback" in data["data"]
        assert "overall_score" in data["data"]["feedback"]
    
    def test_end_dialogue_already_ended(self, client: TestClient):
        """测试重复结束对话"""
        ...
```

### 3. WebSocket对话测试 (test_websocket_dialogue.py)

```python
import pytest
import json

class TestWebSocketDialogue:
    """WebSocket语音对话测试"""
    
    @pytest.mark.asyncio
    async def test_websocket_scene_injection(self, client):
        """测试场景设定注入"""
        # 先创建带场景的对话
        start_resp = client.post("/api/v1/dialogues/start", json={
            "scene": "餐厅点餐"
        })
        conversation_id = start_resp.json()["data"]["conversation_id"]
        
        # 连接WebSocket
        with client.websocket_connect(f"/ws/v1?conversation_id={conversation_id}") as ws:
            # 验证场景设定已注入
            ...
    
    @pytest.mark.asyncio
    async def test_websocket_dialogue_event_storage(self, client, db_session):
        """测试对话事件持久化"""
        conversation_id = "test-conv-001"
        
        with client.websocket_connect(f"/ws/v1?conversation_id={conversation_id}") as ws:
            # 发送音频开始
            ws.send_json({
                "type": "AUDIO_START",
                "request_id": "req-001"
            })
            
            # 模拟ASR结果
            # 验证USER_MESSAGE已写入数据库
            ...
    
    @pytest.mark.asyncio
    async def test_websocket_difficulty_adjustment(self, client):
        """测试WebSocket中的难度调整"""
        # 创建不同级别的对话
        for level in ["beginner", "intermediate", "advanced"]:
            start_resp = client.post("/api/v1/dialogues/start", json={
                "scene": "测试场景",
                "user_level": level
            })
            conversation_id = start_resp.json()["data"]["conversation_id"]
            
            with client.websocket_connect(f"/ws/v1?conversation_id={conversation_id}") as ws:
                # 验证System Prompt包含难度调整
                ...
    
    @pytest.mark.asyncio
    async def test_websocket_barge_in_with_context(self, client):
        """测试打断后的上下文续接"""
        conversation_id = "test-conv-barge"
        
        with client.websocket_connect(f"/ws/v1?conversation_id={conversation_id}") as ws:
            # 开始第一轮对话
            ws.send_json({"type": "AUDIO_START", "request_id": "req-001"})
            # ... 发送音频 ...
            
            # 在AI回复过程中打断
            ws.send_json({"type": "AUDIO_START", "request_id": "req-002"})
            
            # 验证打断上下文已记录
            response = ws.receive_json()
            assert response["type"] == "TASK_ABORTED"
```

### 4. 对话反馈测试 (test_dialogue_feedback.py)

```python
class TestDialogueFeedback:
    """对话反馈生成测试"""
    
    @pytest.mark.asyncio
    async def test_feedback_generation(self):
        """测试反馈生成"""
        from app.domain.dialogue.feedback_generator import generate_feedback
        
        # 模拟对话历史
        dialogue_history = [
            {"role": "user", "text": "I'd like a table for two."},
            {"role": "assistant", "text": "Sure, right this way."},
            {"role": "user", "text": "Can I see the menu?"},
        ]
        
        scene_setting = {
            "scene_name": "餐厅点餐",
            "learning_objectives": ["学会点餐用语"],
            "key_vocabulary": ["menu", "table", "order"]
        }
        
        feedback = await generate_feedback(dialogue_history, scene_setting)
        
        assert "overall_score" in feedback
        assert "strengths" in feedback
        assert "weaknesses" in feedback
        assert "key_vocabulary_mastery" in feedback
    
    @pytest.mark.asyncio
    async def test_feedback_vocabulary_tracking(self):
        """测试词汇掌握度追踪"""
        # 验证核心词汇是否被正确识别为已使用/未使用
        ...
```

### 5. 集成测试 (test_dialogue_integration.py)

```python
@pytest.mark.integration
class TestDialogueIntegration:
    """对话模块集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_dialogue_flow(self, client):
        """测试完整对话流程"""
        # 1. 创建对话
        # 2. WebSocket连接
        # 3. 多轮对话
        # 4. 结束对话
        # 5. 验证反馈
        ...
    
    @pytest.mark.asyncio
    async def test_dialogue_with_real_llm(self):
        """测试真实LLM调用（可选）"""
        # 需要标记为integration测试
        ...
```

---

## 测试工具函数

```python
# tests/conftest.py 或测试工具模块

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

@pytest.fixture
def test_engine():
    """创建测试数据库引擎"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine

@pytest.fixture
def db_session(test_engine):
    """创建测试数据库会话"""
    with Session(test_engine) as session:
        yield session

@pytest.fixture
def client(test_engine):
    """创建测试客户端"""
    from app.main import app
    from app.db import override_engine_for_tests
    
    override_engine_for_tests(test_engine)
    
    from fastapi.testclient import TestClient
    return TestClient(app)

@pytest.fixture
def mock_llm_response():
    """Mock LLM响应"""
    def _mock(response_text: str):
        # 返回mock的chat_complete函数
        ...
    return _mock
```

---

## 验收标准

- [ ] 单元测试覆盖率 > 80%
- [ ] 所有新功能都有对应的测试用例
- [ ] 集成测试验证完整链路
- [ ] 测试能在隔离环境中运行（使用内存数据库）
- [ ] 测试执行时间 < 60秒
- [ ] `pytest tests/ -m "not integration"` 全绿
- [ ] 测试文档完整，包含测试目的和预期行为

---

## 运行命令

```bash
# 运行所有测试
cd backend_fastapi
pytest tests/ -v

# 仅运行单元测试（排除集成测试）
pytest tests/ -m "not integration" -v

# 仅运行对话模块测试
pytest tests/test_scene_engine.py tests/test_dialogue_api.py -v

# 生成覆盖率报告
pytest tests/ --cov=app --cov-report=html

# 运行特定测试
pytest tests/test_dialogue_api.py::TestDialogueAPI::test_start_dialogue_success -v
```

---

## 依赖关系

```
测试模块
    ├── app.domain.dialogue.scene_engine (Agent 01)
    ├── app.routers.dialogue (Agent 02)
    ├── app.main WebSocket (Agent 03)
    └── app.models (已就绪)
```

## 注意事项

1. **测试隔离**: 每个测试用例应独立，不依赖其他测试的状态
2. **Mock外部依赖**: LLM/ASR/TTS调用应使用Mock
3. **异步测试**: 使用 `@pytest.mark.asyncio` 标记异步测试
4. **数据库清理**: 每个测试后清理测试数据
5. **性能考虑**: 避免在单元测试中进行真实网络请求
