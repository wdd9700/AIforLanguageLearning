# AI外语学习系统 - Docker基础设施快速启动指南

## 📋 环境要求

- Docker 24.0+
- Docker Compose 2.23+
- 至少 4GB 可用内存（推荐 8GB）
- 至少 10GB 可用磁盘空间

## 🚀 快速启动

### 1. 克隆并进入项目目录

```bash
cd database_search_layer
```

### 2. 启动所有服务

```bash
docker-compose -f docker-compose.dev.yml up -d
```

### 3. 查看服务状态

```bash
docker-compose -f docker-compose.dev.yml ps
```

### 4. 查看服务日志

```bash
# 查看所有服务日志
docker-compose -f docker-compose.dev.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.dev.yml logs -f postgres
docker-compose -f docker-compose.dev.yml logs -f redis
docker-compose -f docker-compose.dev.yml logs -f elasticsearch
```

## 🔧 服务配置

### PostgreSQL (端口: 5432)

| 配置项 | 值 |
|--------|-----|
| 主机 | localhost |
| 端口 | 5432 |
| 数据库 | aifl_db |
| 用户名 | aifl_user |
| 密码 | aifl_password |

**连接字符串:**
```
postgresql://aifl_user:aifl_password@localhost:5432/aifl_db
```

### Redis (端口: 6379)

| 配置项 | 值 |
|--------|-----|
| 主机 | localhost |
| 端口 | 6379 |
| 内存限制 | 256MB |
| 淘汰策略 | allkeys-lru |

**连接命令:**
```bash
redis-cli -h localhost -p 6379
```

### Elasticsearch (端口: 9200)

| 配置项 | 值 |
|--------|-----|
| HTTP | http://localhost:9200 |
| 内存 | 1GB |
| 插件 | analysis-ik, analysis-pinyin |

**健康检查:**
```bash
curl http://localhost:9200/_cluster/health
```

### Kibana (端口: 5601)

访问地址: http://localhost:5601

## 📝 常用命令

### 启动服务

```bash
# 后台启动所有服务
docker-compose -f docker-compose.dev.yml up -d

# 前台启动（查看实时日志）
docker-compose -f docker-compose.dev.yml up
```

### 停止服务

```bash
# 停止服务（保留数据）
docker-compose -f docker-compose.dev.yml down

# 停止服务并删除数据卷（完全重置）
docker-compose -f docker-compose.dev.yml down -v
```

### 重启服务

```bash
# 重启所有服务
docker-compose -f docker-compose.dev.yml restart

# 重启特定服务
docker-compose -f docker-compose.dev.yml restart postgres
```

### 完全重置

```bash
# 停止并删除所有容器、网络和卷
docker-compose -f docker-compose.dev.yml down -v

# 删除本地数据目录（如果需要）
rm -rf data/postgres data/redis data/elasticsearch

# 重新启动
docker-compose -f docker-compose.dev.yml up -d
```

## 🔍 健康检查

### PostgreSQL 健康检查

```bash
# 使用 psql 连接
docker exec -it aifl_postgres psql -U aifl_user -d aifl_db -c "SELECT version();"

# 检查表是否创建
docker exec -it aifl_postgres psql -U aifl_user -d aifl_db -c "\dt"

# 检查示例数据
docker exec -it aifl_postgres psql -U aifl_user -d aifl_db -c "SELECT COUNT(*) FROM vocabulary;"
```

### Redis 健康检查

```bash
# 检查连接
docker exec -it aifl_redis redis-cli ping

# 查看信息
docker exec -it aifl_redis redis-cli info

# 查看内存使用
docker exec -it aifl_redis redis-cli info memory
```

### Elasticsearch 健康检查

```bash
# 集群健康状态
curl http://localhost:9200/_cluster/health?pretty

# 节点信息
curl http://localhost:9200/_nodes?pretty

# 检查插件
curl http://localhost:9200/_cat/plugins?v

# 测试 IK 分词器
curl -X POST "http://localhost:9200/_analyze?pretty" -H 'Content-Type: application/json' -d'
{
  "analyzer": "ik_max_word",
  "text": "人工智能外语学习系统"
}'

# 测试 Pinyin 分词器
curl -X POST "http://localhost:9200/_analyze?pretty" -H 'Content-Type: application/json' -d'
{
  "analyzer": "pinyin",
  "text": "中文拼音测试"
}'
```

## 🐛 故障排查

### 服务无法启动

#### PostgreSQL

**问题:** 端口被占用
```bash
# 检查端口占用
netstat -ano | findstr :5432

# 停止占用进程或修改 docker-compose.dev.yml 中的端口映射
```

**问题:** 数据卷权限错误
```bash
# 删除并重新创建卷
docker-compose -f docker-compose.dev.yml down -v
docker volume rm database_search_layer_postgres_data
docker-compose -f docker-compose.dev.yml up -d
```

#### Redis

**问题:** 配置文件错误
```bash
# 检查配置文件语法
docker exec -it aifl_redis redis-server /usr/local/etc/redis/redis.conf --test-memory

# 查看启动日志
docker-compose -f docker-compose.dev.yml logs redis
```

#### Elasticsearch

**问题:** 内存不足
```bash
# 增加 Docker 内存限制（Docker Desktop 设置中）
# 或修改 docker-compose.dev.yml 中的 ES_JAVA_OPTS
# - "ES_JAVA_OPTS=-Xms512m -Xmx512m"  # 降低内存使用
```

**问题:** 虚拟内存不足（Linux）
```bash
# 临时增加虚拟内存
sudo sysctl -w vm.max_map_count=262144

# 永久设置
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

**问题:** 插件安装失败
```bash
# 手动进入容器安装插件
docker exec -it aifl_elasticsearch bash
bin/elasticsearch-plugin install analysis-ik
bin/elasticsearch-plugin install analysis-pinyin
```

### 连接问题

#### 无法连接到 PostgreSQL

```bash
# 检查容器状态
docker ps | grep postgres

# 检查日志
docker logs aifl_postgres

# 从容器内部测试连接
docker exec -it aifl_postgres pg_isready -U aifl_user -d aifl_db
```

#### 无法连接到 Redis

```bash
# 检查容器状态
docker ps | grep redis

# 检查日志
docker logs aifl_redis

# 从容器内部测试
docker exec -it aifl_redis redis-cli ping
```

#### 无法连接到 Elasticsearch

```bash
# 检查容器状态
docker ps | grep elasticsearch

# 检查日志
docker logs aifl_elasticsearch

# 等待服务完全启动（首次启动可能需要 30-60 秒）
sleep 30
curl http://localhost:9200
```

### 性能问题

#### PostgreSQL 性能优化

```bash
# 查看当前连接数
docker exec -it aifl_postgres psql -U aifl_user -d aifl_db -c "SELECT count(*) FROM pg_stat_activity;"

# 查看慢查询
docker exec -it aifl_postgres psql -U aifl_user -d aifl_db -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
```

#### Redis 内存使用

```bash
# 查看内存使用情况
docker exec -it aifl_redis redis-cli info memory

# 查看大键
docker exec -it aifl_redis redis-cli --bigkeys

# 清除所有数据（谨慎使用）
docker exec -it aifl_redis redis-cli FLUSHALL
```

## 🔐 环境变量

### 开发环境默认配置

| 服务 | 环境变量 | 默认值 |
|------|----------|--------|
| PostgreSQL | POSTGRES_USER | aifl_user |
| PostgreSQL | POSTGRES_PASSWORD | aifl_password |
| PostgreSQL | POSTGRES_DB | aifl_db |
| PostgreSQL | TZ | Asia/Shanghai |
| Redis | TZ | Asia/Shanghai |
| Elasticsearch | discovery.type | single-node |
| Elasticsearch | xpack.security.enabled | false |
| Elasticsearch | ES_JAVA_OPTS | -Xms1g -Xmx1g |
| Kibana | ELASTICSEARCH_HOSTS | ["http://elasticsearch:9200"] |

### 自定义环境变量

创建 `.env` 文件覆盖默认配置：

```bash
# .env
POSTGRES_USER=myuser
POSTGRES_PASSWORD=mypassword
POSTGRES_DB=mydb
```

然后在 docker-compose 命令中指定：
```bash
docker-compose -f docker-compose.dev.yml --env-file .env up -d
```

## 📊 数据备份与恢复

### PostgreSQL 备份

```bash
# 备份数据库
docker exec -it aifl_postgres pg_dump -U aifl_user -d aifl_db > backup.sql

# 备份特定表
docker exec -it aifl_postgres pg_dump -U aifl_user -d aifl_db -t vocabulary > vocabulary_backup.sql
```

### PostgreSQL 恢复

```bash
# 恢复数据库
docker exec -i aifl_postgres psql -U aifl_user -d aifl_db < backup.sql
```

### Redis 备份

```bash
# 手动触发 BGSAVE
docker exec -it aifl_redis redis-cli BGSAVE

# 复制 RDB 文件
docker cp aifl_redis:/data/dump.rdb ./redis_backup.rdb
```

### Redis 恢复

```bash
# 停止 Redis
docker-compose -f docker-compose.dev.yml stop redis

# 复制备份文件
docker cp ./redis_backup.rdb aifl_redis:/data/dump.rdb

# 启动 Redis
docker-compose -f docker-compose.dev.yml start redis
```

## 📁 文件结构

```
database_search_layer/
├── docker-compose.dev.yml    # Docker Compose 配置
├── QUICKSTART.md             # 本文件
├── requirements.txt          # Python依赖
├── scripts/
│   ├── init_postgres.sql     # PostgreSQL 初始化脚本
│   └── import_vocabulary.py  # 词汇导入脚本
├── config/
│   └── redis.conf            # Redis 配置文件
├── app/                      # Python应用模块
│   ├── __init__.py
│   ├── search/               # 搜索引擎模块
│   │   ├── __init__.py
│   │   ├── es_config.py      # ES映射配置
│   │   └── vocabulary_search.py  # 词汇搜索
│   ├── database/             # 数据库模块
│   │   ├── __init__.py
│   │   └── models.py         # SQLAlchemy模型
│   └── cache/                # 缓存模块
│       ├── __init__.py
│       └── redis_cache.py    # Redis缓存管理
└── data/                     # 数据持久化目录（自动创建）
    ├── postgres/             # PostgreSQL 数据
    ├── redis/                # Redis 数据
    └── elasticsearch/        # Elasticsearch 数据
```

## 🆘 获取帮助

### 查看容器日志

```bash
# 查看最后 100 行日志
docker-compose -f docker-compose.dev.yml logs --tail=100

# 查看特定时间段的日志
docker-compose -f docker-compose.dev.yml logs --since=30m
```

### 进入容器调试

```bash
# PostgreSQL
docker exec -it aifl_postgres bash

# Redis
docker exec -it aifl_redis sh

# Elasticsearch
docker exec -it aifl_elasticsearch bash
```

### 重置单个服务

```bash
# 停止并删除单个服务
docker-compose -f docker-compose.dev.yml stop postgres
docker-compose -f docker-compose.dev.yml rm postgres

# 删除数据卷（谨慎操作）
docker volume rm database_search_layer_postgres_data

# 重新启动
docker-compose -f docker-compose.dev.yml up -d postgres
```

## 🐍 Python模块使用

### 安装依赖

```bash
cd database_search_layer
pip install -r requirements.txt
```

### 词汇搜索示例

```python
import asyncio
from app.search import VocabularySearcher, search_vocabulary

async def main():
    # 创建搜索器
    searcher = VocabularySearcher()
    
    # 搜索词汇（支持模糊搜索）
    results = await searcher.search("happy", fuzzy=True)
    
    for result in results:
        print(f"Word: {result.word}")
        print(f"Definition: {result.definition_zh}")
        print(f"Synonyms: {result.synonyms}")

asyncio.run(main())
```

### 词汇导入示例

```bash
# 创建示例数据
python scripts/import_vocabulary.py sample_data.json --create-sample

# 导入到数据库
python scripts/import_vocabulary.py sample_data.json

# 导入CSV文件
python scripts/import_vocabulary.py vocabulary.csv --type csv
```

### Redis缓存使用

```python
import asyncio
from app.cache import create_cache

async def main():
    # 连接Redis
    cache = await create_cache(host="localhost", port=6379)
    
    # 设置缓存
    await cache.set("key", "value", ttl=300)
    
    # 获取缓存
    value = await cache.get("key")
    
    # 使用分布式锁
    async with cache.lock("resource_lock", timeout=30):
        # 临界区代码
        pass

asyncio.run(main())
```

## ✅ 验收检查清单

- [ ] `docker-compose up -d` 能一键启动所有服务
- [ ] PostgreSQL 自动执行初始化脚本（表结构已创建）
- [ ] Elasticsearch 自动安装 IK 和 Pinyin 插件
- [ ] 所有服务健康检查通过
- [ ] 服务间网络互通正常
- [ ] Kibana 可以访问 Elasticsearch
- [ ] 词汇搜索支持模糊匹配（如 "restarant" → "restaurant"）
- [ ] 词汇搜索支持同义词扩展（如 "happy" → "joyful, pleased"）
- [ ] 搜索响应时间 < 100ms

## 📞 联系方式

如有问题，请联系开发团队或提交 Issue。
