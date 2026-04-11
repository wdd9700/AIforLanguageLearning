"""上下文存储模块测试"""

from __future__ import annotations

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

from app.context_store import (
    ContextStore,
    HybridContextStore,
    RedisContextStore,
    SQLiteContextStore,
    get_context_store,
    set_context_store,
)
from app.db import override_engine_for_tests
from app.model_router import ConversationContext, ConversationMessage


@pytest.fixture(scope="module")
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    override_engine_for_tests(engine)
    SQLModel.metadata.create_all(engine)
    yield None
    override_engine_for_tests(None)


class TestSQLiteContextStore:
    """SQLite 上下文存储测试"""

    def test_save_and_load(self, client) -> None:
        store = SQLiteContextStore()
        context = ConversationContext(
            conversation_id="test-conv-1",
            session_id="test-session",
        )
        context.add_message("system", "You are helpful")
        context.add_message("user", "Hello")

        assert store.save(context) is True

        loaded = store.load("test-conv-1")
        assert loaded is not None
        assert loaded.conversation_id == "test-conv-1"
        assert loaded.session_id == "test-session"
        assert len(loaded.messages) == 2
        assert loaded.messages[0].role == "system"
        assert loaded.messages[1].content == "Hello"

    def test_delete(self, client) -> None:
        store = SQLiteContextStore()
        context = ConversationContext(conversation_id="test-conv-del", session_id="session-del")
        context.add_message("user", "Hi")
        store.save(context)

        assert store.delete("test-conv-del") is True
        assert store.load("test-conv-del") is None

    def test_list_conversations(self, client) -> None:
        store = SQLiteContextStore()
        context = ConversationContext(
            conversation_id="test-conv-list",
            session_id="session-a",
        )
        context.add_message("user", "Hi")
        store.save(context)

        ids = store.list_conversations(session_id="session-a")
        assert "test-conv-list" in ids


class TestRedisContextStore:
    """Redis 上下文存储测试"""

    def test_save_without_redis(self) -> None:
        store = RedisContextStore(redis_url="redis://invalid:9999/0")
        context = ConversationContext(conversation_id="test-redis", session_id="session-redis")
        context.add_message("user", "Hello")
        # 无 Redis 连接时应返回 False
        assert store.save(context) is False

    def test_load_without_redis(self) -> None:
        store = RedisContextStore(redis_url="redis://invalid:9999/0")
        assert store.load("test-redis") is None


class TestHybridContextStore:
    """混合存储测试"""

    def test_fallback_to_sqlite(self, client) -> None:
        store = HybridContextStore(redis_url="redis://invalid:9999/0")
        context = ConversationContext(conversation_id="test-hybrid", session_id="session-hybrid")
        context.add_message("user", "Hello")

        assert store.save(context) is True
        loaded = store.load("test-hybrid")
        assert loaded is not None
        assert loaded.conversation_id == "test-hybrid"

    def test_delete_and_list(self, client) -> None:
        store = HybridContextStore(redis_url="redis://invalid:9999/0")
        context = ConversationContext(
            conversation_id="test-hybrid-2",
            session_id="session-h",
        )
        context.add_message("user", "Hi")
        store.save(context)

        assert store.delete("test-hybrid-2") is True
        assert store.load("test-hybrid-2") is None
        ids = store.list_conversations(session_id="session-h")
        assert "test-hybrid-2" not in ids


class TestContextStoreGlobals:
    """全局存储实例测试"""

    def test_get_and_set_context_store(self) -> None:
        original = get_context_store()
        custom = SQLiteContextStore()
        set_context_store(custom)
        assert get_context_store() is custom
        set_context_store(original)
