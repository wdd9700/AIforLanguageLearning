# VC引导：知识图谱与推荐系统

## 你的任务
构建词汇关系网络和个性化学习推荐引擎。

## 技术栈
- Neo4j 5.x (图数据库)
- Python + neo4j-driver + lightfm + faiss-cpu
- scikit-learn / surprise (协同过滤)

## 核心数据结构

### Neo4j节点
- Word {word, phonetic, meaning, difficulty}
- Tag {name, category}

### Neo4j关系
- (Word)-[:SYNONYM {strength}]->(Word)  // 同义词
- (Word)-[:ANTONYM]->(Word)             // 反义词
- (Word)-[:COGNATE]->(Word)             // 同根词
- (Word)-[:SIMILAR_FORM]->(Word)        // 形近/音近
- (Word)-[:BELONGS_TO]->(Tag)           // 标签归类

## 必须实现的功能

### 知识图谱
- [ ] 词汇关系导入 (从LLM生成结果构建)
- [ ] 同根词识别算法 (词根词缀规则)
- [ ] 近义词检索: `get_synonyms(word, top_k=5)`
- [ ] 词汇学习路径生成 (A*算法)

### 推荐引擎
- [ ] 用户画像建模 (技能水平、薄弱点)
- [ ] LightFM协同过滤模型训练
- [ ] FAISS向量检索 (词汇Embedding)
- [ ] 推荐API: `recommend_vocabulary(user_id, n=10)`

## 推荐算法逻辑
```
输入: 用户薄弱点 + 学习历史 + 当前水平
处理: LightFM矩阵分解 + FAISS相似度检索
输出: Top-N词汇 + 推荐理由
```

## 关键约束
⚠️ 查词未命中时，LLM生成词汇后必须写入知识图谱建立关系
⚠️ 推荐必须考虑: 薄弱点匹配(30%) + 协同过滤(40%) + 内容相似(30%)
⚠️ 同根词关联需LLM提取 + 词根词缀规则双重验证

## 验收标准
- "unhappy" 能召回 "happy" (反义词) + "unfortunate" (近义词)
- 推荐准确率: 用户点击推荐词汇比例 > 30%
- 图谱查询延迟 < 50ms

---

## Copilot引导关键词

```
"使用Neo4j Cypher查询词汇的同义词和反义词"
"实现LightFM矩阵分解推荐算法"
"使用FAISS构建词汇向量索引"
"设计图数据模型存储词汇关系"
"实现基于内容的协同过滤推荐"
```
