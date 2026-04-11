"""Token工具模块 - 提供Token计数和上下文压缩功能

支持多种Tokenizer:
- tiktoken (OpenAI模型)
- 本地模型的近似计数
"""

from __future__ import annotations

import re
from typing import Any

# 尝试导入tiktoken，如果不存在则使用近似计数
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


def get_tokenizer(model_name: str = "gpt-3.5-turbo") -> Any:
    """
    获取适合模型的tokenizer
    
    Args:
        model_name: 模型名称
        
    Returns:
        tokenizer实例或None
    """
    if not TIKTOKEN_AVAILABLE:
        return None
    
    try:
        # 尝试获取对应模型的encoding
        encoding = tiktoken.encoding_for_model(model_name)
        return encoding
    except KeyError:
        # 如果模型不在列表中，使用cl100k_base（支持大多数模型）
        try:
            return tiktoken.get_encoding("cl100k_base")
        except Exception:
            return None


def count_tokens(text: str, model_name: str = "gpt-3.5-turbo") -> int:
    """
    计算文本的Token数量
    
    Args:
        text: 输入文本
        model_name: 模型名称，用于选择tokenizer
        
    Returns:
        int: Token数量
    """
    if not text:
        return 0
    
    tokenizer = get_tokenizer(model_name)
    if tokenizer:
        try:
            tokens = tokenizer.encode(text)
            return len(tokens)
        except Exception:
            pass
    
    # 回退到近似计数
    return approximate_token_count(text)


def approximate_token_count(text: str) -> int:
    """
    近似Token计数（当tiktoken不可用时）
    
    经验法则：
    - 英文：1 token ≈ 4个字符或0.75个单词
    - 中文：1 token ≈ 1-2个字符
    
    Args:
        text: 输入文本
        
    Returns:
        int: 估计的Token数量
    """
    if not text:
        return 0
    
    # 统计字符数
    char_count = len(text)
    
    # 统计中文字符
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    
    # 统计英文单词
    english_words = len(re.findall(r'[a-zA-Z]+', text))
    
    # 估算：中文字符按1.5 token/字，英文按0.75 token/词，其他字符按0.25 token/字符
    estimated = int(
        chinese_chars * 1.5 +
        english_words * 0.75 +
        (char_count - chinese_chars) * 0.25
    )
    
    return max(1, estimated)


def count_messages_tokens(messages: list[dict[str, str]], model_name: str = "gpt-3.5-turbo") -> int:
    """
    计算消息列表的总Token数量
    
    OpenAI的token计算规则：
    - 每条消息额外消耗4个token（格式开销）
    - 角色名称消耗token
    - 内容消耗token
    
    Args:
        messages: OpenAI格式的消息列表
        model_name: 模型名称
        
    Returns:
        int: 总Token数量
    """
    if not messages:
        return 0
    
    total = 0
    
    for msg in messages:
        # 每条消息的格式开销
        total += 4
        
        # 角色名称
        role = msg.get("role", "")
        total += count_tokens(role, model_name)
        
        # 内容
        content = msg.get("content", "")
        total += count_tokens(content, model_name)
    
    # 对话格式额外开销
    total += 2
    
    return total


def truncate_by_tokens(
    text: str,
    max_tokens: int,
    model_name: str = "gpt-3.5-turbo",
    from_end: bool = True
) -> str:
    """
    按Token数量截断文本
    
    Args:
        text: 输入文本
        max_tokens: 最大Token数
        model_name: 模型名称
        from_end: 是否从末尾保留（True=保留末尾，False=保留开头）
        
    Returns:
        str: 截断后的文本
    """
    if not text:
        return text
    
    tokenizer = get_tokenizer(model_name)
    if tokenizer:
        try:
            tokens = tokenizer.encode(text)
            if len(tokens) <= max_tokens:
                return text
            
            if from_end:
                truncated = tokens[-max_tokens:]
            else:
                truncated = tokens[:max_tokens]
            
            return tokenizer.decode(truncated)
        except Exception:
            pass
    
    # 回退到字符截断（粗略估计）
    # 假设平均每个token约4个字符
    max_chars = max_tokens * 4
    
    if len(text) <= max_chars:
        return text
    
    if from_end:
        return "..." + text[-max_chars+3:]
    else:
        return text[:max_chars-3] + "..."


def summarize_context(
    messages: list[dict[str, str]],
    max_summary_tokens: int = 200,
    model_name: str = "gpt-3.5-turbo"
) -> str:
    """
    生成对话上下文的摘要
    
    当上下文超过Token限制时，将历史对话压缩为摘要。
    保留system消息，压缩user/assistant对话。
    
    Args:
        messages: 消息列表
        max_summary_tokens: 摘要的最大token数
        model_name: 模型名称
        
    Returns:
        str: 摘要文本
    """
    if not messages:
        return ""
    
    # 分离system消息和普通对话
    system_msgs = [m for m in messages if m.get("role") == "system"]
    conversation = [m for m in messages if m.get("role") != "system"]
    
    if not conversation:
        # 只有system消息，直接返回
        return "\n".join(m.get("content", "") for m in system_msgs)
    
    # 提取关键信息
    topics = []
    key_points = []
    
    for msg in conversation:
        content = msg.get("content", "").strip()
        if not content:
            continue
        
        role = msg.get("role", "")
        
        # 提取用户的主要话题（前50个字符）
        if role == "user":
            topic = content[:50] + "..." if len(content) > 50 else content
            topics.append(f"用户询问: {topic}")
        
        # 提取关键结论（包含"总结"、"结论"等的句子）
        elif role == "assistant":
            # 简单启发式：找包含关键词的句子
            sentences = re.split(r'[。！？.!?]', content)
            for sent in sentences:
                if any(kw in sent for kw in ["总结", "结论", "关键", "重要", "建议", "注意"]):
                    if len(sent) > 10:  # 过滤太短的片段
                        key_points.append(sent.strip())
                        break  # 只取第一个
    
    # 构建摘要
    summary_parts = []
    
    if system_msgs:
        system_content = system_msgs[0].get("content", "")
        if system_content:
            summary_parts.append(f"[场景设定: {system_content[:100]}...]")
    
    if topics:
        summary_parts.append("对话主题:")
        summary_parts.extend(topics[-3:])  # 最近3个主题
    
    if key_points:
        summary_parts.append("关键信息:")
        summary_parts.extend(key_points[-3:])  # 最近3个关键点
    
    summary = "\n".join(summary_parts)
    
    # 确保摘要不超长
    return truncate_by_tokens(summary, max_summary_tokens, model_name, from_end=False)


def compress_messages(
    messages: list[dict[str, str]],
    max_tokens: int = 4000,
    model_name: str = "gpt-3.5-turbo"
) -> list[dict[str, str]]:
    """
    压缩消息列表到指定Token数以内
    
    策略：
    1. 保留所有system消息
    2. 保留最近的几轮完整对话
    3. 更早的对话压缩为摘要
    
    Args:
        messages: 原始消息列表
        max_tokens: 最大Token数
        model_name: 模型名称
        
    Returns:
        list[dict[str, str]]: 压缩后的消息列表
    """
    if not messages:
        return messages
    
    current_tokens = count_messages_tokens(messages, model_name)
    if current_tokens <= max_tokens:
        return messages
    
    # 分离system消息
    system_msgs = [m for m in messages if m.get("role") == "system"]
    conversation = [m for m in messages if m.get("role") != "system"]
    
    system_tokens = count_messages_tokens(system_msgs, model_name)
    available_for_conv = max_tokens - system_tokens - 200  # 预留200给摘要
    
    if available_for_conv < 500:
        # 空间太小，只保留system和最后一轮
        if conversation:
            return system_msgs + conversation[-2:] if len(conversation) >= 2 else system_msgs + conversation
        return system_msgs
    
    # 从后往前找能完整保留的对话轮数
    preserved = []
    preserved_tokens = 0
    
    for msg in reversed(conversation):
        msg_tokens = count_tokens(msg.get("content", ""), model_name) + 4  # +4格式开销
        if preserved_tokens + msg_tokens <= available_for_conv * 0.6:  # 60%给完整对话
            preserved.insert(0, msg)
            preserved_tokens += msg_tokens
        else:
            break
    
    # 剩余部分生成摘要
    older_msgs = conversation[:-len(preserved)] if preserved else conversation
    if older_msgs:
        summary = summarize_context(older_msgs, int(available_for_conv * 0.4), model_name)
        if summary:
            summary_msg = {
                "role": "system",
                "content": f"[历史对话摘要] {summary}"
            }
            return system_msgs + [summary_msg] + preserved
    
    return system_msgs + preserved


# 导出函数
__all__ = [
    "count_tokens",
    "approximate_token_count",
    "count_messages_tokens",
    "truncate_by_tokens",
    "summarize_context",
    "compress_messages",
    "get_tokenizer",
    "TIKTOKEN_AVAILABLE",
]