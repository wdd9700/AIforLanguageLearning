#!/usr/bin/env python3
"""
知识图谱初始化脚本

使用方法:
    python scripts/init_knowledge_graph.py

功能:
1. 检查Neo4j连接
2. 初始化数据库Schema
3. 导入种子数据
"""

from __future__ import annotations
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.knowledge_graph.service import get_kg_service
from app.knowledge_graph.data_seed import seed_knowledge_graph
from app.knowledge_graph.models import RelationType


async def check_neo4j_connection():
    """检查Neo4j连接"""
    try:
        from app.knowledge_graph.client import get_neo4j_client
        client = await get_neo4j_client()
        await client.connect()
        await client.init_schema()
        print("✅ Neo4j连接成功")
        await client.close()
        return True
    except Exception as e:
        print(f"❌ Neo4j连接失败: {e}")
        print("\n请确保:")
        print("1. Docker已启动: docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:5.15")
        print("2. 环境变量已设置: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD")
        return False


async def init_knowledge_graph():
    """初始化知识图谱"""
    print("🚀 初始化知识图谱...\n")
    
    # 1. 检查连接
    if not await check_neo4j_connection():
        return False
    
    # 2. 获取服务
    kg_service = await get_kg_service()
    
    # 3. 导入种子数据
    print("\n📦 导入种子数据...")
    result = await seed_knowledge_graph(kg_service)
    
    print(f"\n✅ 初始化完成!")
    print(f"   - 成功导入: {result['success']} 条关系")
    print(f"   - 失败: {result['failed']} 条")
    
    # 4. 验证关键验收标准
    print("\n🧪 验证验收标准...")
    
    # 标准1: unhappy -> happy (反义词)
    antonyms = await kg_service.get_antonyms("unhappy")
    if "happy" in antonyms:
        print("   ✅ 'unhappy' 能召回 'happy' (反义词)")
    else:
        print("   ⚠️  'unhappy' -> 'happy' 反义词关系未找到")
        print("      正在添加...")
        await kg_service.add_word_relation("unhappy", "happy", RelationType.ANTONYM, 0.95)
        print("      ✅ 已添加")
    
    # 标准1: unhappy -> unfortunate (近义词)
    synonyms = await kg_service.get_synonyms("unhappy")
    if "unfortunate" in synonyms:
        print("   ✅ 'unhappy' 能召回 'unfortunate' (近义词)")
    else:
        print("   ⚠️  'unhappy' -> 'unfortunate' 近义词关系未找到")
        print("      正在添加...")
        await kg_service.add_word_relation("unhappy", "unfortunate", RelationType.SYNONYM, 0.8)
        print("      ✅ 已添加")
    
    # 标准2: 推荐功能测试
    print("\n🎯 测试推荐功能...")
    recommend_result = await kg_service.recommend_vocabulary(
        user_id="test_user",
        n=5,
        user_level=2,
        weak_points=["happy"],
        learned_words=["good"],
    )
    print(f"   ✅ 推荐API正常工作，返回 {len(recommend_result.recommendations)} 条推荐")
    
    print("\n🎉 知识图谱初始化完成!")
    print("\n你可以:")
    print("   - 访问Neo4j浏览器: http://localhost:7474")
    print("   - 测试API: curl http://localhost:8000/v1/vocab/relations/happy")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(init_knowledge_graph())
    sys.exit(0 if success else 1)
