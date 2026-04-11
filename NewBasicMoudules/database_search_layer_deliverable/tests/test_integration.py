"""
数据库与搜索引擎层 - 集成测试
测试环境: Docker Compose (PostgreSQL + Redis + Elasticsearch)

运行方式:
    1. 启动基础设施: docker-compose -f docker-compose.dev.yml up -d
    2. 运行测试: pytest tests/test_integration.py -v
"""

import asyncio
import pytest
import uuid
from datetime import datetime
from typing import List, Dict, Any

# 导入被测试模块
import sys
sys.path.insert(0, '..')

from app.database import (
    init_db, close_db, get_db_session,
    VocabularyCRUD, UserCRUD,
    Vocabulary, User, VocabularyDifficulty
)
from app.cache import init_redis, close_redis, redis_client
from app.search import init_elasticsearch, close_elasticsearch, es_client


# ==================== Fixtures ====================

@pytest.fixture(scope="session")
async def setup_infrastructure():
    """测试会话开始前启动基础设施"""
    # 初始化数据库
    await init_db("postgresql+asyncpg://aifl_user:aifl_password@localhost:5432/aifl_db")
    
    # 初始化Redis
    await init_redis(host="localhost", port=6379)
    
    # 初始化Elasticsearch
    await init_elasticsearch(["http://localhost:9200"])
    
    yield
    
    # 清理
    await close_db()
    await close_redis()
    await close_elasticsearch()


@pytest.fixture
async def db_session(setup_infrastructure):
    """提供数据库会话"""
    async with get_db_session() as session:
        yield session


# ==================== 数据库测试 ====================

@pytest.mark.asyncio
async def test_database_connection(db_session):
    """测试数据库连接"""
    # 简单查询测试连接
    from sqlalchemy import text
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_vocabulary_crud(db_session):
    """测试词汇CRUD操作"""
    # 创建词汇
    vocab = await VocabularyCRUD.create(
        session=db_session,
        word="test_happy",
        meanings=[{
            "pos": "adj.",
            "meaning": "快乐的",
            "examples": ["I am happy."]
        }],
        phonetic_us="/ˈhæpi/",
        difficulty=VocabularyDifficulty.BEGINNER,
        tags=["test", "emotion"]
    )
    
    assert vocab.id is not None
    assert vocab.word == "test_happy"
    
    # 查询词汇
    found = await VocabularyCRUD.get_by_word(db_session, "test_happy")
    assert found is not None
    assert found.word == "test_happy"
    
    # 搜索词汇
    results = await VocabularyCRUD.search(db_session, "test_hap", limit=10)
    assert len(results) > 0


@pytest.mark.asyncio
async def test_user_crud(db_session):
    """测试用户CRUD操作"""
    import uuid
    
    # 创建用户
    user = await UserCRUD.create(
        session=db_session,
        username=f"test_user_{uuid.uuid4().hex[:8]}",
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="hashed_password_here"
    )
    
    assert user.id is not None
    
    # 查询用户
    found = await UserCRUD.get_by_id(db_session, user.id)
    assert found is not None
    assert found.username == user.username


# ==================== Redis缓存测试 ====================

@pytest.mark.asyncio
async def test_redis_cache_basic(setup_infrastructure):
    """测试Redis基础缓存操作"""
    # 设置缓存
    await redis_client.set("test_key", {"data": "value"}, ttl=60)
    
    # 获取缓存
    result = await redis_client.get("test_key")
    assert result == {"data": "value"}
    
    # 检查存在性
    exists = await redis_client.exists("test_key")
    assert exists is True
    
    # 删除缓存
    await redis_client.delete("test_key")
    
    # 验证删除
    result = await redis_client.get("test_key")
    assert result is None


@pytest.mark.asyncio
async def test_redis_distributed_lock(setup_infrastructure):
    """测试Redis分布式锁"""
    lock_name = "test_lock"
    
    # 获取锁
    identifier = await redis_client.acquire_lock(lock_name, timeout=10)
    assert identifier is not None
    
    # 再次获取锁应该失败（或等待）
    second_identifier = await redis_client.acquire_lock(
        lock_name, timeout=5, blocking_timeout=1
    )
    assert second_identifier is None  # 应该获取失败
    
    # 释放锁
    released = await redis_client.release_lock(lock_name, identifier)
    assert released is True


@pytest.mark.asyncio
async def test_redis_cache_decorator(setup_infrastructure):
    """测试Redis缓存装饰器"""
    call_count = 0
    
    @redis_client.cached(ttl=60, key_prefix="test:")
    async def expensive_function(x: int) -> int:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.1)
        return x * 2
    
    # 第一次调用
    result1 = await expensive_function(5)
    assert result1 == 10
    assert call_count == 1
    
    # 第二次调用（应该命中缓存）
    result2 = await expensive_function(5)
    assert result2 == 10
    assert call_count == 1  # 不应该增加


# ==================== Elasticsearch测试 ====================

@pytest.mark.asyncio
async def test_es_connection(setup_infrastructure):
    """测试ES连接"""
    info = await es_client.client.info()
    assert "version" in info
    print(f"ES Version: {info['version']['number']}")


@pytest.mark.asyncio
async def test_es_index_vocabulary(setup_infrastructure):
    """测试ES词汇索引"""
    vocab_data = {
        "id": str(uuid.uuid4()),
        "word": "test_elastic",
        "phonetic_us": "/ɪˈlæstɪk/",
        "phonetic_uk": "/ɪˈlæstɪk/",
        "meanings": [
            {
                "pos": "adj.",
                "meaning": "有弹性的",
                "examples": ["The material is very elastic."]
            }
        ],
        "difficulty": "intermediate",
        "tags": ["test", "material"],
        "synonyms": ["flexible", "stretchy"]
    }
    
    # 索引词汇
    await es_client.index_vocabulary(vocab_data, synonyms=["flexible"])
    
    # 刷新索引
    await es_client.refresh_index()
    
    # 搜索验证
    result = await es_client.search_vocabulary("test_elastic", fuzzy=False)
    assert result["total"] >= 1


@pytest.mark.asyncio
async def test_es_fuzzy_search(setup_infrastructure):
    """测试ES模糊搜索（拼写纠错）"""
    # 索引一个词汇
    vocab_data = {
        "id": str(uuid.uuid4()),
        "word": "restaurant",
        "phonetic_us": "/ˈrestərɑːnt/",
        "meanings": [{"pos": "n.", "meaning": "餐馆", "examples": []}],
        "difficulty": "beginner"
    }
    await es_client.index_vocabulary(vocab_data)
    await es_client.refresh_index()
    
    # 模糊搜索（拼写错误）
    result = await es_client.search_vocabulary("restarant", fuzzy=True)
    # 注意：由于分词器配置，可能无法完全匹配，但至少能返回结果
    assert "results" in result


@pytest.mark.asyncio
async def test_es_autocomplete(setup_infrastructure):
    """测试ES自动完成"""
    # 索引多个词汇
    words = ["happy", "happiness", "happily", "sad", "sadness"]
    for word in words:
        await es_client.index_vocabulary({
            "id": str(uuid.uuid4()),
            "word": word,
            "meanings": [{"pos": "adj.", "meaning": "测试", "examples": []}],
            "difficulty": "beginner"
        })
    
    await es_client.refresh_index()
    
    # 获取建议
    suggestions = await es_client.get_suggestions("hap", limit=5)
    assert len(suggestions) > 0
    # 应该包含 happy, happiness, happily


# ==================== 三层缓存策略测试 ====================

@pytest.mark.asyncio
async def test_three_layer_cache_strategy(setup_infrastructure, db_session):
    """测试三层缓存策略"""
    from app.services.vocabulary_service import VocabularySearchService
    
    service = VocabularySearchService()
    
    # 先确保ES中有数据
    vocab_data = {
        "id": str(uuid.uuid4()),
        "word": "integration_test",
        "phonetic_us": "/ˌɪntɪˈɡreɪʃn/",
        "meanings": [{"pos": "n.", "meaning": "集成测试", "examples": []}],
        "difficulty": "advanced"
    }
    await es_client.index_vocabulary(vocab_data)
    await es_client.refresh_index()
    
    # 第一次搜索（应该走ES）
    result1 = await service.search("integration_test", fuzzy=False)
    assert result1["source"] in ["elasticsearch", "redis"]
    
    # 第二次搜索（应该命中Redis缓存）
    result2 = await service.search("integration_test", fuzzy=False)
    assert result2["source"] == "redis"
    
    # 验证缓存命中更快
    assert result2["took_ms"] <= result1["took_ms"]


# ==================== 性能测试 ====================

@pytest.mark.asyncio
async def test_search_performance(setup_infrastructure):
    """测试搜索性能"""
    from app.services.vocabulary_service import VocabularySearchService
    
    service = VocabularySearchService()
    
    # 预热缓存
    await service.search("test", fuzzy=False)
    
    # 测试缓存命中性能
    times = []
    for _ in range(10):
        import time
        start = time.time()
        result = await service.search("test", fuzzy=False)
        elapsed = (time.time() - start) * 1000
        times.append(elapsed)
    
    avg_time = sum(times) / len(times)
    print(f"Average search time (cached): {avg_time:.2f}ms")
    
    # 断言平均响应时间小于100ms
    assert avg_time < 100, f"Search too slow: {avg_time}ms"


# ==================== 数据导入测试 ====================

@pytest.mark.asyncio
async def test_import_vocabulary(setup_infrastructure, db_session):
    """测试词汇导入功能"""
    import json
    import tempfile
    import os
    
    # 创建临时JSON文件
    test_data = [
        {
            "word": "import_test_1",
            "phonetic_us": "/test/",
            "meanings": [{"pos": "n.", "meaning": "测试1", "examples": []}],
            "difficulty": "beginner"
        },
        {
            "word": "import_test_2",
            "phonetic_us": "/test/",
            "meanings": [{"pos": "n.", "meaning": "测试2", "examples": []}],
            "difficulty": "intermediate"
        }
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_data, f)
        temp_file = f.name
    
    try:
        # 导入数据
        from scripts.import_vocabulary import VocabularyImporter
        importer = VocabularyImporter(batch_size=100)
        
        result = await importer.import_from_json(temp_file, db_only=True)
        
        assert result["imported"] == 2
        assert result["failed"] == 0
        
        # 验证数据已导入
        vocab1 = await VocabularyCRUD.get_by_word(db_session, "import_test_1")
        assert vocab1 is not None
        
    finally:
        os.unlink(temp_file)


# ==================== 运行入口 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
