# 知识图谱模块 - 使用指南

> 成员C: 知识图谱和推荐系统

## 快速开始

### 1. 安装Neo4j

**Windows (最简单的方式):**
```powershell
# 使用Docker
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5.15
```

**访问:**
- 浏览器界面: http://localhost:7474
- 默认账号: neo4j / password

### 2. 安装Python依赖

```bash
cd backend_fastapi
pip install neo4j lightfm faiss-cpu numpy scikit-learn
```

### 3. 配置环境变量

```bash
# .env 文件
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

### 4. 初始化数据

```python
# 在Python中运行
import asyncio
from app.knowledge_graph.service import get_kg_service
from app.knowledge_graph.data_seed import seed_knowledge_graph

async def init():
    kg_service = await get_kg_service()
    await seed_knowledge_graph(kg_service)
    print("数据初始化完成!")

asyncio.run(init())
```

## API使用示例

### 查询词汇关系

```bash
# 查询反义词
curl -X GET "http://localhost:8000/v1/vocab/relations/unhappy?relation_type=antonym"

# 响应
{
  "word": "unhappy",
  "relations": [
    {"word": "happy", "relation_type": "antonym", "strength": 0.95}
  ],
  "total": 1
}
```

### 获取词汇推荐

```bash
# 推荐词汇
curl -X POST "http://localhost:8000/v1/vocab/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "count": 5,
    "user_level": 2,
    "weak_points": ["happy"],
    "learned_words": ["good"]
  }'
```

### 添加词汇关系

```bash
# 添加同义词关系
curl -X POST "http://localhost:8000/v1/vocab/relations/add" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "difficult",
    "target": "hard",
    "relation_type": "synonym",
    "strength": 0.9
  }'
```

## 核心概念速查

### 词汇关系类型

| 类型 | 说明 | 示例 |
|------|------|------|
| synonym | 同义词 | happy ↔ joyful |
| antonym | 反义词 | happy ↔ sad |
| cognate | 同根词 | happy ↔ happiness |
| similar_form | 形近词 | book ↔ look |

### 推荐算法逻辑

```
输入: 用户薄弱点 + 学习历史 + 当前水平
      ↓
处理: 1. 薄弱点匹配(30%): 推荐薄弱点同义词
      2. 难度匹配(40%): 推荐适合难度的词
      3. 关系扩展(30%): 从已学词汇扩展
      ↓
输出: Top-N词汇 + 推荐理由
```

## 验收标准验证

### 标准1: 关系查询
```bash
# 验证 "unhappy" 能召回 "happy" (反义词)
curl "http://localhost:8000/v1/vocab/relations/unhappy?relation_type=antonym"

# 验证 "unhappy" 能召回 "unfortunate" (近义词)
curl "http://localhost:8000/v1/vocab/relations/unhappy?relation_type=synonym"
```

### 标准2: 推荐准确率
```bash
# 获取推荐并检查是否有合理结果
curl -X POST "http://localhost:8000/v1/vocab/recommend" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "count": 10}'
```

### 标准3: 查询延迟
```bash
# 测试查询延迟 (< 50ms)
time curl "http://localhost:8000/v1/vocab/relations/happy"
```

## 项目结构

```
app/knowledge_graph/
├── __init__.py          # 模块导出
├── models.py            # 数据模型 (Pydantic)
├── client.py            # Neo4j客户端
├── service.py           # 业务逻辑
├── data_seed.py         # 种子数据
└── README.md            # 本文件
```

## 学习路径建议

### 第1天: 理解基础
1. **Neo4j基础**: 理解节点(Node)和关系(Relationship)
2. **Cypher查询**: 学习基本的MATCH查询
3. **运行代码**: 启动Neo4j，运行测试

### 第2天: 深入理解
1. **推荐算法**: 理解混合推荐策略
2. **代码阅读**: 阅读service.py的实现
3. **扩展功能**: 尝试添加新功能

### 推荐学习资源

| 主题 | 资源 | 时间 |
|------|------|------|
| Neo4j基础 | [Neo4j Graph Academy](https://neo4j.com/graphacademy/) | 2小时 |
| Cypher查询 | [Cypher Cheat Sheet](https://neo4j.com/docs/cypher-cheat-sheet/) | 30分钟 |
| 图数据库概念 | [Graph Databases Book](https://neo4j.com/book-graph-databases/) | 选读 |

## 常见问题

### Q: Neo4j连接失败?
**A:** 检查:
1. Docker容器是否运行: `docker ps | grep neo4j`
2. 端口是否正确: 7474 (HTTP), 7687 (Bolt)
3. 认证信息是否正确

### Q: 查询没有结果?
**A:** 
1. 确认已运行数据初始化: `seed_knowledge_graph()`
2. 检查Neo4j浏览器中是否有数据
3. 确认查询的词汇存在

### Q: 推荐结果不准确?
**A:**
1. 当前是简化版算法，需要更多用户数据
2. 可以调整 `recommend_vocabulary` 中的权重
3. 考虑集成LightFM进行矩阵分解

## 下一步优化

1. **LightFM集成**: 实现真正的协同过滤
2. **FAISS向量检索**: 基于词向量的相似度推荐
3. **实时更新**: 用户学习行为实时更新推荐
4. **A/B测试**: 验证推荐效果

## 联系

有问题? 查看:
- 项目文档: `docs/development_guide/`
- 团队知识: `docs/team_onboarding/`
