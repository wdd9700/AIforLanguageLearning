# VC引导：数据库与搜索引擎层

## 你的任务
搭建AI外语学习系统的数据持久化和全文检索基础设施。

## 技术栈
- PostgreSQL 15+ (主数据库)
- Elasticsearch 8.x (全文检索)
- Redis 7+ (缓存层)
- Python + SQLAlchemy + elasticsearch-py

## 核心表结构要求
1. **词汇表(vocabulary)**: word, phonetic, meaning, example, difficulty, tags[]
2. **用户表(users)**: profile, learning_level, preferences
3. **学习记录表(learning_logs)**: user_id, content_type, content_id, score, timestamp
4. **对话历史表(dialogue_history)**: session_id, messages[], scene_context

## 必须实现的功能
- [ ] PostgreSQL表结构 + 索引优化
- [ ] Elasticsearch映射配置(支持拼音、模糊搜索)
- [ ] 词汇数据导入脚本(从JSON/CSV批量导入)
- [ ] 查询接口封装: `search_vocabulary(query, fuzzy=True)` 
- [ ] 同义词/反义词检索API

## 关键约束
⚠️ 词汇搜索必须支持: 同根词匹配、同义词扩展、编辑距离容错
⚠️ 查词流程: Redis缓存 → Elasticsearch → PostgreSQL(兜底)
⚠️ 所有搜索接口响应时间 < 100ms

## 验收标准
- 10万词汇数据导入无性能问题
- "restarant" 能匹配到 "restaurant" (拼写纠错)
- "happy" 能召回 "joyful, pleased, cheerful" (同义词)

---

## Copilot引导关键词

```
"使用PostgreSQL JSONB存储词汇标签"
"配置Elasticsearch ik分词器支持拼音搜索"
"实现Redis分布式锁防止缓存击穿"
"使用SQLAlchemy异步会话管理数据库连接"
"设计PostgreSQL分区表存储学习记录"
```
