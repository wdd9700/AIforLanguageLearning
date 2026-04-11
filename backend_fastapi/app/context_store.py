"""上下文存储模块 - 提供对话上下文的持久化存储

支持：
- SQLite持久化（默认）
- Redis支持（可选）
- 自动保存和恢复
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlmodel import Session, select

from .db import get_engine
from .model_router import ConversationContext, ConversationMessage

logger = logging.getLogger(__name__)


class ContextStore:
    """上下文存储基类"""
    
    def save(self, context: ConversationContext) -> bool:
        """保存上下文"""
        raise NotImplementedError
    
    def load(self, conversation_id: str) -> ConversationContext | None:
        """加载上下文"""
        raise NotImplementedError
    
    def delete(self, conversation_id: str) -> bool:
        """删除上下文"""
        raise NotImplementedError
    
    def list_conversations(self, session_id: str | None = None) -> list[str]:
        """列出现有对话ID"""
        raise NotImplementedError


class SQLiteContextStore(ContextStore):
    """SQLite上下文存储"""
    
    def __init__(self) -> None:
        self._engine = get_engine()
    
    def save(self, context: ConversationContext) -> bool:
        """
        保存上下文到SQLite
        
        使用ConversationEvent表存储消息历史
        """
        try:
            from .models import ConversationEvent
            
            with Session(self._engine) as session:
                # 获取当前最大seq
                existing = session.exec(
                    select(ConversationEvent).where(
                        ConversationEvent.conversation_id == context.conversation_id
                    )
                ).all()
                
                existing_seqs = {e.seq for e in existing}
                
                # 保存新消息
                for i, msg in enumerate(context.messages):
                    if i in existing_seqs:
                        continue  # 跳过已存在的
                    
                    event = ConversationEvent(
                        conversation_id=context.conversation_id,
                        session_id=context.session_id,
                        seq=i,
                        type="MESSAGE",
                        ts=int(msg.timestamp * 1000),
                        payload={
                            "role": msg.role,
                            "content": msg.content,
                            "token_count": msg.token_count,
                        }
                    )
                    session.add(event)
                
                session.commit()
                logger.debug(f"Saved context {context.conversation_id} with {len(context.messages)} messages")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save context {context.conversation_id}: {e}")
            return False
    
    def load(self, conversation_id: str) -> ConversationContext | None:
        """从SQLite加载上下文"""
        try:
            from .models import ConversationEvent
            
            with Session(self._engine) as session:
                events = session.exec(
                    select(ConversationEvent).where(
                        ConversationEvent.conversation_id == conversation_id
                    ).order_by(ConversationEvent.seq)
                ).all()
                
                if not events:
                    return None
                
                # 重建上下文
                first_event = events[0]
                context = ConversationContext(
                    conversation_id=conversation_id,
                    session_id=first_event.session_id,
                )
                
                for event in events:
                    if event.type == "MESSAGE" and isinstance(event.payload, dict):
                        msg = ConversationMessage(
                            role=event.payload.get("role", "user"),
                            content=event.payload.get("content", ""),
                            timestamp=event.ts / 1000,
                            token_count=event.payload.get("token_count", 0),
                        )
                        context.messages.append(msg)
                
                logger.debug(f"Loaded context {conversation_id} with {len(context.messages)} messages")
                return context
                
        except Exception as e:
            logger.error(f"Failed to load context {conversation_id}: {e}")
            return None
    
    def delete(self, conversation_id: str) -> bool:
        """删除上下文"""
        try:
            from .models import ConversationEvent
            
            with Session(self._engine) as session:
                events = session.exec(
                    select(ConversationEvent).where(
                        ConversationEvent.conversation_id == conversation_id
                    )
                ).all()
                
                for event in events:
                    session.delete(event)
                
                session.commit()
                logger.debug(f"Deleted context {conversation_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete context {conversation_id}: {e}")
            return False
    
    def list_conversations(self, session_id: str | None = None) -> list[str]:
        """列出现有对话ID"""
        try:
            from .models import ConversationEvent
            
            with Session(self._engine) as session:
                query = select(ConversationEvent.conversation_id).distinct()
                if session_id:
                    query = query.where(ConversationEvent.session_id == session_id)
                
                results = session.exec(query).all()
                return list(results)
                
        except Exception as e:
            logger.error(f"Failed to list conversations: {e}")
            return []


class RedisContextStore(ContextStore):
    """Redis上下文存储（可选）"""
    
    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = redis_url
        self._redis: Any | None = None
        self._try_connect()
    
    def _try_connect(self) -> bool:
        """尝试连接Redis"""
        try:
            import redis
            url = self._redis_url or "redis://localhost:6379/0"
            self._redis = redis.from_url(url, decode_responses=True)
            self._redis.ping()
            logger.info("Redis context store connected")
            return True
        except Exception as e:
            logger.warning(f"Redis not available: {e}")
            self._redis = None
            return False
    
    def _get_key(self, conversation_id: str) -> str:
        """生成Redis键"""
        return f"aifl:context:{conversation_id}"
    
    def save(self, context: ConversationContext) -> bool:
        """保存上下文到Redis"""
        if not self._redis:
            return False
        
        try:
            key = self._get_key(context.conversation_id)
            data = {
                "conversation_id": context.conversation_id,
                "session_id": context.session_id,
                "messages": [
                    {
                        "role": m.role,
                        "content": m.content,
                        "timestamp": m.timestamp,
                        "token_count": m.token_count,
                    }
                    for m in context.messages
                ],
            }
            
            # 使用JSON序列化，设置7天过期
            self._redis.setex(key, 7 * 24 * 3600, json.dumps(data))
            return True
            
        except Exception as e:
            logger.error(f"Failed to save context to Redis: {e}")
            return False
    
    def load(self, conversation_id: str) -> ConversationContext | None:
        """从Redis加载上下文"""
        if not self._redis:
            return None
        
        try:
            key = self._get_key(conversation_id)
            data_str = self._redis.get(key)
            
            if not data_str:
                return None
            
            data = json.loads(data_str)
            context = ConversationContext(
                conversation_id=data["conversation_id"],
                session_id=data.get("session_id", ""),
            )
            
            for msg_data in data.get("messages", []):
                msg = ConversationMessage(
                    role=msg_data["role"],
                    content=msg_data["content"],
                    timestamp=msg_data.get("timestamp", 0),
                    token_count=msg_data.get("token_count", 0),
                )
                context.messages.append(msg)
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to load context from Redis: {e}")
            return None
    
    def delete(self, conversation_id: str) -> bool:
        """删除上下文"""
        if not self._redis:
            return False
        
        try:
            key = self._get_key(conversation_id)
            self._redis.delete(key)
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete context from Redis: {e}")
            return False
    
    def list_conversations(self, session_id: str | None = None) -> list[str]:
        """列出现有对话ID"""
        if not self._redis:
            return []
        
        try:
            pattern = self._get_key("*")
            keys = self._redis.keys(pattern)
            conversation_ids = [k.replace("aifl:context:", "") for k in keys]
            
            # 如果指定了session_id，需要过滤
            if session_id:
                filtered = []
                for cid in conversation_ids:
                    context = self.load(cid)
                    if context and context.session_id == session_id:
                        filtered.append(cid)
                return filtered
            
            return conversation_ids
            
        except Exception as e:
            logger.error(f"Failed to list conversations from Redis: {e}")
            return []


class HybridContextStore(ContextStore):
    """混合存储：Redis优先，失败时回退到SQLite"""
    
    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_store = RedisContextStore(redis_url)
        self._sqlite_store = SQLiteContextStore()
    
    def save(self, context: ConversationContext) -> bool:
        """保存到Redis和SQLite"""
        redis_ok = self._redis_store.save(context)
        sqlite_ok = self._sqlite_store.save(context)
        return redis_ok or sqlite_ok
    
    def load(self, conversation_id: str) -> ConversationContext | None:
        """优先从Redis加载，失败时从SQLite加载"""
        # 优先Redis
        context = self._redis_store.load(conversation_id)
        if context:
            return context
        
        # 回退到SQLite
        return self._sqlite_store.load(conversation_id)
    
    def delete(self, conversation_id: str) -> bool:
        """从两个存储中删除"""
        redis_ok = self._redis_store.delete(conversation_id)
        sqlite_ok = self._sqlite_store.delete(conversation_id)
        return redis_ok or sqlite_ok
    
    def list_conversations(self, session_id: str | None = None) -> list[str]:
        """合并两个存储的结果"""
        redis_ids = set(self._redis_store.list_conversations(session_id))
        sqlite_ids = set(self._sqlite_store.list_conversations(session_id))
        return list(redis_ids | sqlite_ids)


# 全局存储实例
_store: ContextStore | None = None


def get_context_store() -> ContextStore:
    """获取全局上下文存储实例"""
    global _store
    if _store is None:
        # 默认使用混合存储
        _store = HybridContextStore()
    return _store


def init_context_store(redis_url: str | None = None, use_sqlite_only: bool = False) -> ContextStore:
    """
    初始化上下文存储
    
    Args:
        redis_url: Redis连接URL
        use_sqlite_only: 是否只使用SQLite
        
    Returns:
        ContextStore: 存储实例
    """
    global _store
    
    if use_sqlite_only:
        _store = SQLiteContextStore()
    else:
        _store = HybridContextStore(redis_url)
    
    return _store


__all__ = [
    "ContextStore",
    "SQLiteContextStore",
    "RedisContextStore",
    "HybridContextStore",
    "get_context_store",
    "init_context_store",
]