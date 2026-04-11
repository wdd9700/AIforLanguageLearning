"""
Neo4j 客户端

学习要点:
- 使用上下文管理器管理连接
- 异步操作提高性能
- 环境变量配置连接信息

安装依赖:
pip install neo4j
"""

from __future__ import annotations
import os
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from neo4j import AsyncGraphDatabase, AsyncSession
from neo4j.exceptions import Neo4jError


class Neo4jClient:
    """
    Neo4j 异步客户端
    
    使用方法:
        async with get_neo4j_client() as client:
            result = await client.get_word_relations("happy")
    """
    
    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        self.driver = None
    
    async def connect(self) -> "Neo4jClient":
        """建立连接"""
        self.driver = AsyncGraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password)
        )
        return self
    
    async def close(self):
        """关闭连接"""
        if self.driver:
            await self.driver.close()
            self.driver = None
    
    async def __aenter__(self) -> "Neo4jClient":
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    # ==================== 词汇节点操作 ====================
    
    async def create_word(
        self,
        word: str,
        phonetic: Optional[str] = None,
        meaning: Optional[str] = None,
        difficulty: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """
        创建词汇节点
        
        Cypher查询说明:
        - MERGE: 如果节点不存在则创建，存在则返回已有节点
        - ON CREATE SET: 只在创建时设置属性
        """
        if not self.driver:
            raise RuntimeError("Client not connected")
        
        tags = tags or []
        
        query = """
        MERGE (w:Word {word: $word})
        ON CREATE SET 
            w.phonetic = $phonetic,
            w.meaning = $meaning,
            w.difficulty = $difficulty,
            w.tags = $tags,
            w.created_at = datetime()
        RETURN w
        """
        
        try:
            async with self.driver.session() as session:
                await session.run(
                    query,
                    word=word,
                    phonetic=phonetic,
                    meaning=meaning,
                    difficulty=difficulty,
                    tags=tags,
                )
                return True
        except Neo4jError as e:
            print(f"Neo4j error creating word: {e}")
            return False
    
    async def get_word(self, word: str) -> Optional[Dict[str, Any]]:
        """获取词汇信息"""
        if not self.driver:
            raise RuntimeError("Client not connected")
        
        query = """
        MATCH (w:Word {word: $word})
        RETURN w.word as word, w.phonetic as phonetic, 
               w.meaning as meaning, w.difficulty as difficulty,
               w.tags as tags
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, word=word)
            record = await result.single()
            return dict(record) if record else None
    
    # ==================== 词汇关系操作 ====================
    
    async def create_relation(
        self,
        source: str,
        target: str,
        relation_type: str,
        strength: float = 1.0,
    ) -> bool:
        """
        创建词汇关系
        
        关系类型: synonym, antonym, cognate, similar_form
        """
        if not self.driver:
            raise RuntimeError("Client not connected")
        
        # 确保两个词汇节点存在
        await self.create_word(source)
        await self.create_word(target)
        
        # 动态构建关系类型（Cypher不支持参数化关系类型）
        query = f"""
        MATCH (a:Word {{word: $source}}), (b:Word {{word: $target}})
        MERGE (a)-[r:{relation_type.upper()}]->(b)
        ON CREATE SET r.strength = $strength, r.created_at = datetime()
        ON MATCH SET r.strength = $strength
        RETURN r
        """
        
        try:
            async with self.driver.session() as session:
                await session.run(
                    query,
                    source=source,
                    target=target,
                    strength=strength,
                )
                return True
        except Neo4jError as e:
            print(f"Neo4j error creating relation: {e}")
            return False
    
    async def get_relations(
        self,
        word: str,
        relation_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        获取词汇关系
        
        如果不指定relation_type，返回所有类型的关系
        """
        if not self.driver:
            raise RuntimeError("Client not connected")
        
        if relation_type:
            # 查询特定类型的关系
            query = f"""
            MATCH (w:Word {{word: $word}})-[r:{relation_type.upper()}]->(related:Word)
            RETURN related.word as word, r.strength as strength, 
                   COALESCE(related.meaning, '') as meaning, 
                   COALESCE(related.difficulty, 1) as difficulty,
                   '{relation_type}' as relation_type
            LIMIT $limit
            """
        else:
            # 查询所有类型的关系
            query = """
            MATCH (w:Word {word: $word})-[r]->(related:Word)
            RETURN related.word as word, r.strength as strength,
                   COALESCE(related.meaning, '') as meaning, 
                   COALESCE(related.difficulty, 1) as difficulty,
                   type(r) as relation_type
            LIMIT $limit
            """
        
        async with self.driver.session() as session:
            result = await session.run(query, word=word, limit=limit)
            records = await result.data()
            return records
    
    async def get_antonyms(self, word: str) -> List[Dict[str, Any]]:
        """获取反义词 - 验收标准关键功能"""
        return await self.get_relations(word, relation_type="antonym", limit=5)
    
    async def get_synonyms(self, word: str) -> List[Dict[str, Any]]:
        """获取同义词"""
        return await self.get_relations(word, relation_type="synonym", limit=5)
    
    async def get_cognates(self, word: str) -> List[Dict[str, Any]]:
        """获取同根词"""
        return await self.get_relations(word, relation_type="cognate", limit=5)
    
    # ==================== 初始化 ====================
    
    async def init_schema(self):
        """初始化数据库Schema（创建约束和索引）"""
        if not self.driver:
            raise RuntimeError("Client not connected")
        
        queries = [
            # 创建词汇唯一约束
            "CREATE CONSTRAINT word_unique IF NOT EXISTS FOR (w:Word) REQUIRE w.word IS UNIQUE",
            # 创建索引
            "CREATE INDEX word_difficulty IF NOT EXISTS FOR (w:Word) ON (w.difficulty)",
        ]
        
        async with self.driver.session() as session:
            for query in queries:
                try:
                    await session.run(query)
                except Neo4jError as e:
                    print(f"Schema init warning: {e}")


# 全局客户端实例（单例模式）
_neo4j_client: Optional[Neo4jClient] = None


async def get_neo4j_client() -> Neo4jClient:
    """
    获取Neo4j客户端实例
    
    使用方式:
        client = await get_neo4j_client()
        async with client:
            result = await client.get_word("happy")
    """
    global _neo4j_client
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient()
    return _neo4j_client
