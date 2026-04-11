"""模块E: 模型路由与上下文管理

核心职责:
1. 多模型统一路由 (Kimi API + 本地Qwen)
2. 场景化模型选择 (chat/vocab/essay/scenario_expansion)
3. 故障自动切换
4. 对话上下文管理 (滑动窗口、Token压缩)
5. Prompt模板管理
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator

import httpx

logger = logging.getLogger(__name__)

from .context_store import get_context_store
from .prompts import render_prompt
from .retry_utils import RETRY_CONFIG_LLM_API, retry_async
from .runtime_config import get_runtime_config, get_scene_model, update_runtime_config
from .settings import settings
from .token_utils import (
    compress_messages,
    count_messages_tokens,
    count_tokens,
)


class SceneType(str, Enum):
    """场景类型枚举"""
    CHAT = "chat"                    # 对话执行 → 本地Qwen
    VOCAB = "vocab"                  # 词汇生成 → Kimi API
    ESSAY = "essay"                  # 作文批改 → Kimi API
    SCENARIO_EXPANSION = "scenario_expansion"  # 场景扩写 → Kimi API (thinking)


class ModelProvider(str, Enum):
    """模型提供商枚举"""
    LOCAL = "local"      # 本地模型 (Ollama/vLLM)
    KIMI = "kimi"        # Kimi API


@dataclass
class ModelEndpoint:
    """模型端点配置"""
    provider: ModelProvider
    base_url: str
    api_key: str
    model_id: str
    timeout_connect: float = 5.0
    timeout_read: float = 30.0
    priority: int = 0  # 优先级，数字越小优先级越高


@dataclass  
class RoutingDecision:
    """路由决策结果"""
    scene: SceneType
    primary_endpoint: ModelEndpoint
    fallback_endpoints: list[ModelEndpoint] = field(default_factory=list)
    use_streaming: bool = True
    temperature: float = 0.7


@dataclass
class ConversationMessage:
    """对话消息"""
    role: str  # system/user/assistant
    content: str
    timestamp: float = field(default_factory=time.time)
    token_count: int = 0


@dataclass
class ConversationContext:
    """对话上下文"""
    conversation_id: str
    session_id: str
    messages: list[ConversationMessage] = field(default_factory=list)
    max_messages: int = 20  # 保留最近20轮
    max_tokens: int = 4000  # 上下文Token上限
    token_threshold: float = 0.8  # 80%触发摘要
    
    def add_message(self, role: str, content: str, token_count: int = 0) -> None:
        """添加消息，维护滑动窗口"""
        # 如果没有提供token_count，自动计算
        if token_count == 0 and content:
            token_count = count_tokens(content)
        
        msg = ConversationMessage(
            role=role,
            content=content,
            token_count=token_count
        )
        self.messages.append(msg)
        
        # 保留最近N轮 (每轮 = user + assistant)
        max_total = self.max_messages * 2
        if len(self.messages) > max_total:
            # 保留system消息和最近的消息
            system_msgs = [m for m in self.messages if m.role == "system"]
            other_msgs = [m for m in self.messages if m.role != "system"]
            other_msgs = other_msgs[-(max_total - len(system_msgs)):]
            self.messages = system_msgs + other_msgs
    
    def get_total_tokens(self) -> int:
        """获取总Token数"""
        return sum(m.token_count for m in self.messages)
    
    def should_compress(self) -> bool:
        """判断是否需要压缩上下文"""
        return self.get_total_tokens() > self.max_tokens * self.token_threshold
    
    def compress_if_needed(self) -> bool:
        """
        如果需要，压缩上下文
        
        Returns:
            bool: 是否进行了压缩
        """
        if not self.should_compress():
            return False
        
        # 转换为OpenAI格式并压缩
        messages = self.to_openai_messages()
        compressed = compress_messages(messages, self.max_tokens)
        
        # 重建消息列表
        self.messages = []
        for msg in compressed:
            self.add_message(msg["role"], msg["content"])
        
        return True
    
    def to_openai_messages(self) -> list[dict[str, str]]:
        """转换为OpenAI格式"""
        return [{"role": m.role, "content": m.content} for m in self.messages]


class ModelRouter:
    """模型路由器 - 核心类"""
    
    # 场景到模型提供商的映射
    SCENE_PROVIDER_MAP: dict[SceneType, ModelProvider] = {
        SceneType.CHAT: ModelProvider.LOCAL,
        SceneType.VOCAB: ModelProvider.KIMI,
        SceneType.ESSAY: ModelProvider.KIMI,
        SceneType.SCENARIO_EXPANSION: ModelProvider.KIMI,
    }
    
    def __init__(self) -> None:
        self._endpoints: dict[ModelProvider, list[ModelEndpoint]] = {}
        self._contexts: dict[str, ConversationContext] = {}
        self._init_endpoints()
    
    def _init_endpoints(self) -> None:
        """初始化模型端点配置"""
        # 本地模型端点
        local_endpoint = ModelEndpoint(
            provider=ModelProvider.LOCAL,
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model_id=settings.llm_model,
            timeout_connect=5.0,
            timeout_read=60.0,  # 本地模型可能需要更长时间
            priority=1
        )
        self._endpoints[ModelProvider.LOCAL] = [local_endpoint]
        
        # Kimi API端点 (从环境变量或运行时配置读取)
        kimi_base_url = self._get_kimi_base_url()
        kimi_api_key = self._get_kimi_api_key()
        if kimi_base_url and kimi_api_key:
            kimi_endpoint = ModelEndpoint(
                provider=ModelProvider.KIMI,
                base_url=kimi_base_url,
                api_key=kimi_api_key,
                model_id="kimi-latest",  # 或其他具体模型
                timeout_connect=5.0,
                timeout_read=30.0,
                priority=1
            )
            self._endpoints[ModelProvider.KIMI] = [kimi_endpoint]
    
    def _get_kimi_base_url(self) -> str:
        """获取Kimi API基础URL"""
        # 优先从运行时配置读取
        runtime = get_runtime_config()
        kimi_config = runtime.get("kimi", {})
        base_url = kimi_config.get("base_url", "")
        if base_url:
            return base_url
        # 从环境变量读取
        import os
        return os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1")
    
    def _get_kimi_api_key(self) -> str:
        """获取Kimi API密钥"""
        runtime = get_runtime_config()
        kimi_config = runtime.get("kimi", {})
        api_key = kimi_config.get("api_key", "")
        if api_key:
            return api_key
        import os
        return os.getenv("KIMI_API_KEY", "")
    
    def route(self, scene: SceneType | str) -> RoutingDecision:
        """
        根据场景路由到合适的模型
        
        Args:
            scene: 场景类型
            
        Returns:
            RoutingDecision: 路由决策结果
        """
        if isinstance(scene, str):
            scene = SceneType(scene)
        
        # 获取场景对应的提供商
        provider = self.SCENE_PROVIDER_MAP.get(scene, ModelProvider.LOCAL)
        
        # 获取该提供商的端点列表
        endpoints = self._endpoints.get(provider, [])
        if not endpoints:
            # 回退到本地模型
            endpoints = self._endpoints.get(ModelProvider.LOCAL, [])
        
        # 按优先级排序
        endpoints = sorted(endpoints, key=lambda e: e.priority)
        
        primary = endpoints[0] if endpoints else None
        fallbacks = endpoints[1:] if len(endpoints) > 1 else []
        
        # 场景扩写使用thinking模式，需要不同的temperature
        temperature = 0.7
        if scene == SceneType.SCENARIO_EXPANSION:
            temperature = 0.9  # 更高的创造性
        elif scene == SceneType.ESSAY:
            temperature = 0.5  # 更稳定的评分
        
        return RoutingDecision(
            scene=scene,
            primary_endpoint=primary,
            fallback_endpoints=fallbacks,
            use_streaming=True,
            temperature=temperature
        )
    
    def get_or_create_context(
        self,
        conversation_id: str,
        session_id: str = "",
        system_prompt: str = "",
        load_from_store: bool = True
    ) -> ConversationContext:
        """
        获取或创建对话上下文
        
        Args:
            conversation_id: 对话ID
            session_id: 会话ID
            system_prompt: 系统提示词
            load_from_store: 是否尝试从存储加载
            
        Returns:
            ConversationContext: 对话上下文
        """
        if conversation_id not in self._contexts:
            # 尝试从存储加载
            if load_from_store:
                try:
                    store = get_context_store()
                    loaded = store.load(conversation_id)
                    if loaded:
                        self._contexts[conversation_id] = loaded
                        logger.debug(f"Loaded context {conversation_id} from store")
                        return loaded
                except Exception as e:
                    logger.warning(f"Failed to load context {conversation_id}: {e}")
            
            # 创建新上下文
            context = ConversationContext(
                conversation_id=conversation_id,
                session_id=session_id
            )
            if system_prompt:
                context.add_message("system", system_prompt)
            self._contexts[conversation_id] = context
        
        return self._contexts[conversation_id]
    
    def save_context(self, conversation_id: str) -> bool:
        """
        保存对话上下文到存储
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            bool: 是否保存成功
        """
        context = self._contexts.get(conversation_id)
        if not context:
            return False
        
        try:
            store = get_context_store()
            return store.save(context)
        except Exception as e:
            logger.error(f"Failed to save context {conversation_id}: {e}")
            return False
    
    def clear_context(self, conversation_id: str) -> None:
        """清除对话上下文"""
        if conversation_id in self._contexts:
            del self._contexts[conversation_id]
    
    async def call_with_fallback(
        self,
        decision: RoutingDecision,
        messages: list[dict[str, str]],
        stream: bool = True
    ) -> AsyncIterator[str]:
        """
        调用模型，支持故障切换
        
        Args:
            decision: 路由决策
            messages: 消息列表
            stream: 是否流式输出
            
        Yields:
            str: 生成的文本块
        """
        endpoints = [decision.primary_endpoint] + decision.fallback_endpoints
        
        last_error = None
        for endpoint in endpoints:
            try:
                async for chunk in self._call_endpoint(endpoint, messages, stream, decision.temperature):
                    yield chunk
                return  # 成功，结束
            except Exception as e:
                last_error = e
                continue  # 尝试下一个端点
        
        # 所有端点都失败
        raise RuntimeError(f"All model endpoints failed. Last error: {last_error}")
    
    async def _call_endpoint_with_retry(
        self,
        endpoint: ModelEndpoint,
        messages: list[dict[str, str]],
        stream: bool,
        temperature: float
    ) -> AsyncIterator[str]:
        """调用具体端点（带指数退避重试）"""
        
        async def _make_request() -> AsyncIterator[str]:
            timeout = httpx.Timeout(
                endpoint.timeout_read,
                connect=endpoint.timeout_connect
            )
            
            async with httpx.AsyncClient(base_url=endpoint.base_url, timeout=timeout) as client:
                payload = {
                    "model": endpoint.model_id,
                    "messages": messages,
                    "stream": stream,
                    "temperature": temperature
                }
                
                if stream:
                    async with client.stream(
                        "POST",
                        "/chat/completions",
                        headers={"Authorization": f"Bearer {endpoint.api_key}"},
                        json=payload
                    ) as resp:
                        resp.raise_for_status()
                        async for line in resp.aiter_lines():
                            if line.startswith("data: "):
                                data = line[6:]
                                if data == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(data)
                                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield content
                                except json.JSONDecodeError:
                                    continue
                else:
                    resp = await client.post(
                        "/chat/completions",
                        headers={"Authorization": f"Bearer {endpoint.api_key}"},
                        json=payload
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    yield content
        
        # 使用指数退避重试
        # 注意：由于这是生成器，我们不能直接包装整个函数
        # 而是在call_with_fallback层面处理重试
        async for chunk in _make_request():
            yield chunk
    
    async def _call_endpoint(
        self,
        endpoint: ModelEndpoint,
        messages: list[dict[str, str]],
        stream: bool,
        temperature: float
    ) -> AsyncIterator[str]:
        """调用具体端点（带重试逻辑）"""
        last_error: Exception | None = None
        config = RETRY_CONFIG_LLM_API
        
        for attempt in range(config.max_retries + 1):
            try:
                async for chunk in self._call_endpoint_with_retry(
                    endpoint, messages, stream, temperature
                ):
                    yield chunk
                return  # 成功，结束
            except Exception as e:
                last_error = e
                
                if attempt >= config.max_retries:
                    logger.error(
                        f"Endpoint {endpoint.provider.value} failed after {config.max_retries + 1} attempts. "
                        f"Last error: {e}"
                    )
                    raise
                
                from .retry_utils import calculate_delay
                delay = calculate_delay(attempt, config)
                
                logger.warning(
                    f"Endpoint {endpoint.provider.value} failed (attempt {attempt + 1}). "
                    f"Retrying in {delay:.2f}s. Error: {e}"
                )
                
                await asyncio.sleep(delay)


# 全局路由器实例
_router: ModelRouter | None = None


def get_model_router() -> ModelRouter:
    """获取全局模型路由器实例"""
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router


async def expand_scenario(user_description: str, language: str = "en") -> str:
    """
    场景扩写: 用户描述 → Kimi API扩写 → 结构化场景描述
    
    Args:
        user_description: 用户的场景描述
        language: 目标语言
        
    Returns:
        str: 扩写后的场景描述（可作为System Prompt）
    """
    router = get_model_router()
    decision = router.route(SceneType.SCENARIO_EXPANSION)
    
    # 构建扩写Prompt
    prompt = f"""请将用户的简短场景描述扩写为一个详细的口语练习场景设定。

用户描述: {user_description}
目标语言: {language}

请输出一个结构化的场景描述，包含:
1. 场景背景设定
2. 用户角色
3. AI角色
4. 对话目标
5. 关键话题点

输出格式为纯文本，直接可用作System Prompt。"""
    
    messages = [
        {"role": "system", "content": "你是一个专业的英语口语练习场景设计师。"},
        {"role": "user", "content": prompt}
    ]
    
    result = ""
    async for chunk in router.call_with_fallback(decision, messages, stream=False):
        result += chunk
    
    return result.strip()


async def chat_with_context(
    conversation_id: str,
    user_message: str,
    session_id: str = "",
    system_prompt: str = ""
) -> AsyncIterator[str]:
    """
    带上下文的对话: 使用本地Qwen模型
    
    Args:
        conversation_id: 对话ID
        user_message: 用户消息
        session_id: 会话ID
        system_prompt: 系统提示词
        
    Yields:
        str: 生成的文本块
    """
    router = get_model_router()
    
    # 获取或创建上下文
    context = router.get_or_create_context(conversation_id, session_id, system_prompt)
    
    # 检查是否需要压缩上下文
    if context.should_compress():
        context.compress_if_needed()
    
    # 添加用户消息
    context.add_message("user", user_message)
    
    # 路由决策
    decision = router.route(SceneType.CHAT)
    
    # 调用模型
    messages = context.to_openai_messages()
    assistant_response = ""
    
    async for chunk in router.call_with_fallback(decision, messages, stream=True):
        assistant_response += chunk
        yield chunk
    
    # 保存助手回复到上下文
    context.add_message("assistant", assistant_response)
    
    # 持久化上下文
    router.save_context(conversation_id)


async def generate_vocab_with_routing(term: str, language: str = "en") -> dict[str, Any]:
    """
    词汇生成: 使用Kimi API生成结构化词汇信息
    
    Args:
        term: 词汇
        language: 目标语言
        
    Returns:
        dict: 包含meaning、example、example_translation、definitions的结构化数据
    """
    router = get_model_router()
    decision = router.route(SceneType.VOCAB)
    
    prompt = f"""请为单词"{term}"生成详细的词汇解析。

要求输出以下JSON格式:
{{
    "meaning": "中文释义（简洁）",
    "example": "英文例句",
    "example_translation": "例句中文翻译",
    "definitions": [
        {{
            "meaning": "义项1中文解释",
            "example": "义项1例句",
            "example_translation": "义项1例句翻译"
        }}
    ]
}}

注意:
1. 必须输出有效的JSON格式
2. 至少提供2-3个不同义项
3. 例句要体现该义项的典型用法"""

    messages = [
        {"role": "system", "content": "你是一个专业的英语词汇解析专家。只输出JSON格式，不要有任何其他文字。"},
        {"role": "user", "content": prompt}
    ]
    
    result = ""
    async for chunk in router.call_with_fallback(decision, messages, stream=False):
        result += chunk
    
    # 解析JSON结果
    try:
        # 尝试直接解析
        data = json.loads(result.strip())
    except json.JSONDecodeError:
        # 尝试从代码块中提取
        import re
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', result, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
            except json.JSONDecodeError:
                data = {"meaning": result[:200], "example": "", "example_translation": "", "definitions": []}
        else:
            # 尝试提取最大的JSON对象
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                try:
                    data = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    data = {"meaning": result[:200], "example": "", "example_translation": "", "definitions": []}
            else:
                data = {"meaning": result[:200], "example": "", "example_translation": "", "definitions": []}
    
    # 确保返回格式正确
    return {
        "meaning": data.get("meaning", ""),
        "example": data.get("example", ""),
        "example_translation": data.get("example_translation", ""),
        "definitions": data.get("definitions", []),
    }


async def grade_essay_with_routing(
    essay_text: str,
    language: str = "en",
    criteria: list[str] | None = None
) -> dict[str, Any]:
    """
    作文批改: 使用Kimi API进行多维度评分
    
    Args:
        essay_text: 作文文本
        language: 语言
        criteria: 评分维度列表，默认使用6个维度
        
    Returns:
        dict: 包含score、dimensions、feedback、corrected的结构化评分结果
    """
    router = get_model_router()
    decision = router.route(SceneType.ESSAY)
    
    if criteria is None:
        criteria = ["词汇", "语法", "逻辑", "流畅度", "内容", "结构"]
    
    prompt = f"""请对以下作文进行专业批改和评分。

作文内容:
```{language}
{essay_text}
```

请从以下维度进行评分（0-100分）:
{', '.join(criteria)}

输出以下JSON格式:
{{
    "total_score": 85,
    "dimensions": {{
        "词汇": {{"score": 80, "comment": "词汇使用评价"}},
        "语法": {{"score": 85, "comment": "语法使用评价"}},
        ...
    }},
    "overall_feedback": "总体评价和建议",
    "errors": [
        {{"text": "错误文本", "correction": "修正", "explanation": "解释"}}
    ],
    "corrected_version": "修正后的完整作文"
}}

注意:
1. 必须输出有效的JSON格式
2. 每个维度都要有具体的评价说明
3. 列出3-5个主要错误并给出修正"""

    messages = [
        {"role": "system", "content": "你是一个专业的英语作文批改专家。只输出JSON格式，不要有任何其他文字。"},
        {"role": "user", "content": prompt}
    ]
    
    result = ""
    async for chunk in router.call_with_fallback(decision, messages, stream=False):
        result += chunk
    
    # 解析JSON结果
    try:
        data = json.loads(result.strip())
    except json.JSONDecodeError:
        import re
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', result, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
            except json.JSONDecodeError:
                data = {"parse_error": True, "raw_response": result[:500]}
        else:
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                try:
                    data = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    data = {"parse_error": True, "raw_response": result[:500]}
            else:
                data = {"parse_error": True, "raw_response": result[:500]}
    
    return data


# 导出关键组件
__all__ = [
    "ModelRouter",
    "ModelEndpoint",
    "RoutingDecision",
    "ConversationContext",
    "ConversationMessage",
    "SceneType",
    "ModelProvider",
    "get_model_router",
    "expand_scenario",
    "chat_with_context",
    "generate_vocab_with_routing",
    "grade_essay_with_routing",
]