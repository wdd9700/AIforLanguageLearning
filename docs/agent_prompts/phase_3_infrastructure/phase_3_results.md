# 基础设施加固方案

**报告生成日期**: 2026年4月12日  
**评估依据**: `phase_2_results.md`、代码仓库实际结构、`docker-compose.dev.yml`、`docker-compose.infra.yml`  
**评估范围**: `backend_fastapi` 基础设施基线与成员2（基础设施）交付物缺口

---

## 1. 现状评估

### 1.1 已具备的基础设施
- **PostgreSQL 16**: `docker-compose.dev.yml` 已编排 `postgres:16-alpine`，含健康检查
- **Redis 7 单机版**: `docker-compose.dev.yml` 已编排 `redis:7-alpine`，含健康检查
- **Elasticsearch 8.11.0 单节点**: `docker-compose.dev.yml` 已编排，用于词汇全文搜索
- **Neo4j 5.15 Community**: `docker-compose.dev.yml` 已编排，用于知识图谱存储
- **RabbitMQ 3.12-management**: `docker-compose.infra.yml` 已编排，用于 Celery 消息 broker
- **MinIO**: `docker-compose.infra.yml` 已编排，用于对象存储
- **Prometheus 指标基线**: `app/infrastructure/telemetry/metrics.py` 已实现 `PrometheusMetricsCollector` 和 `/metrics` 端点
- **TraceID 中间件**: `app/infrastructure/telemetry/tracing.py` 已实现 `TraceMiddleware` 和 `contextvars` 追踪
- **Redis 缓存兼容层**: `app/infrastructure/persistence/cache/redis_cache.py` 已实现连接、get/set/delete
- **Celery 配置占位**: `app/infrastructure/messaging/celery_app.py` 已配置队列路由和优先级
- **接口契约**: `persistence/`、`messaging/`、`storage/`、`telemetry/` 层均已定义 Protocol

### 1.2 缺失或薄弱的基础设施
- **PostgreSQL 连接池**: 未配置 `asyncpg` + `SQLAlchemy` 异步连接池参数
- **Alembic 迁移脚本**: `pyproject.toml` 已依赖 `alembic>=1.13`，但无初始化目录和迁移脚本
- **Redis 高可用**: 当前仅单机版，技术栈要求 Cluster（3主3从）或哨兵模式
- **Elasticsearch 搜索实现**: `VocabularySearcher.search()` 为占位，返回空列表
- **Celery Worker 实际任务**: `celery_app.py` 仅有配置，无 `tasks.py` 和作文批改/词汇生成任务函数
- **MinIO FastAPI 集成**: `FileStorage` Protocol 已定义，但无上传路由和预签名 URL 实现
- **死信队列 (DLQ)**: RabbitMQ 未配置死信交换机和重试策略
- **分布式锁**: 无 Redis Redlock 或类似实现
- **读写分离**: 数据库层未设计只读副本路由
- **监控可观测性深度链路**: 无 Grafana Dashboard、ELK Stack、ClickHouse 时序数据库
- **请求链路监控中间件**: `/metrics` 端点已挂载，但 `TraceMiddleware` 未实际注册到 FastAPI 请求生命周期
- **成员2 交付物**: `NewBasicMoudules/team_onboarding/infrastructure/` 完全为空，无 README、无 Docker 配置、无测试

### 1.3 技术债务
- **成员2 基础设施代码缺失**: 评分 4.65/10，基础设施目录为空，需要从头设计并补全 Docker Compose、README、FastAPI 集成示例和测试
- **成员6 监控代码滞后**: 评分 2.55/10，Prometheus 基线已搭但 ClickHouse/ELK/Grafana 完全未实现
- **大量占位模块待填充**: ES 搜索、MinIO 上传、Celery 任务、数据库迁移等均为空实现或仅 Protocol
- **Redis 单机与生产要求差距**: 技术栈文档要求 Cluster，当前仅单机，需评估本地部署场景下的折中方案

---

## 2. 加固目标

- **目标1**: 补齐 Alembic 数据库迁移体系，实现版本化 schema 管理
- **目标2**: 强化 PostgreSQL 连接池与 Redis 缓存层，使其达到生产可用标准
- **目标3**: 填充消息队列（Celery + RabbitMQ）和文件存储（MinIO）的实际实现，打通异步任务与上传链路
- **目标4**: 建立基础可观测性体系：请求指标自动采集、结构化日志统一输出、TraceID 全链路透传
- **目标5**: 所有基础设施服务必须能通过 `docker-compose.dev.yml` + `docker-compose.infra.yml` 在本地 PC（AMD 9950X3D + RTX 5080）上一键启动

---

## 3. 分领域方案

### 3.1 数据库层

**现状**: PostgreSQL 16 容器已就绪，但 `backend_fastapi` 中缺少 Alembic 初始化目录和迁移脚本。当前使用 `SQLModel.metadata.create_all()` 创建表，不适合后续迭代。`get_engine()` 使用默认同步连接，未显式配置连接池大小和超时。

**目标**: 建立 Alembic 迁移体系，配置异步连接池，为后续读写分离预留扩展点。

**方案**:
1. 初始化 Alembic: `cd backend_fastapi && alembic init alembic`
2. 修改 `alembic/env.py` 使用异步引擎 (`sqlalchemy.ext.asyncio`)
3. 将 `sqlmodel.SQLModel.metadata` 绑定到 Alembic target metadata
4. 生成初始迁移脚本，覆盖 `User`、`ConversationEvent` 等已有模型
5. 在 `app/db.py` 中配置 `AsyncEngine` 连接池参数：`pool_size=10`, `max_overflow=20`, `pool_timeout=30`
6. 将 `get_engine()` 升级为返回 `AsyncEngine`，并在路由层使用 `AsyncSession`

**技术选型**: `alembic>=1.13`, `sqlmodel>=0.0.21`, `asyncpg`

**配置示例**:
```python
# backend_fastapi/app/db.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

DATABASE_URL = "postgresql+asyncpg://aifl_user:aifl_password@localhost:5432/aifl_db"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
)

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_async_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

```python
# backend_fastapi/alembic/env.py (关键片段)
from sqlmodel import SQLModel
from app.domain import models  # noqa

target_metadata = SQLModel.metadata

from sqlalchemy.ext.asyncio import create_async_engine

config = context.config
url = config.get_main_option("sqlalchemy.url")
connectable = create_async_engine(url, poolclass=pool.NullPool)
```

---

### 3.2 缓存层

**现状**: `RedisCache` 已实现单机版连接和基本 get/set/delete，但未实现分布式锁、缓存策略（如 Cache-Aside）、以及 Redis 故障时的降级逻辑。

**目标**: 强化缓存层，增加分布式锁和缓存策略封装；考虑到本地部署场景，Redis Cluster 延后，但需保留切换能力。

**方案**:
1. 在 `RedisCache` 基础上增加 `lock(key, timeout)` 方法，使用 `redis.lock.Lock` 实现分布式锁
2. 增加 `CacheAside` 装饰器/辅助类，封装“先查缓存、再查数据库、回写缓存”模式
3. 增加 Redis 连接失败时的静默降级：所有缓存方法在连接不可用时返回 `None` 或 `False`，不阻塞业务
4. 保留 Cluster 配置扩展点：在 `RedisCache.__init__` 中预留 `startup_nodes` 参数，后续可无缝切换为 `redis.asyncio.RedisCluster`

**技术选型**: `redis>=5.0` (单机), `redis.asyncio.RedisCluster` (未来扩展)

**配置示例**:
```python
# backend_fastapi/app/infrastructure/persistence/cache/redis_cache.py
import asyncio
from typing import Any, Optional

class RedisCache:
    # ... existing code ...

    async def lock(self, key: str, timeout: int = 10) -> Any:
        if not self._client or not self._connected:
            return None
        return self._client.lock(self._make_key(f"lock:{key}"), timeout=timeout)

    async def get_or_set(
        self,
        key: str,
        factory: callable,
        ttl: Optional[int] = None,
    ) -> Any:
        cached = await self.get(key)
        if cached is not None:
            return cached
        value = await factory()
        await self.set(key, value, ttl=ttl)
        return value
```

---

### 3.3 搜索层

**现状**: Elasticsearch 8.11.0 容器已就绪，但 `VocabularySearcher.search()` 为占位实现，返回空列表。无索引创建脚本和 mappings 定义。

**目标**: 实现词汇全文搜索，包括索引初始化、同义词扩展、模糊查询，并提供索引管理脚本。

**方案**:
1. 在 `app/infrastructure/persistence/search/` 下新建 `es_client.py`，封装 `elasticsearch[async]` 客户端
2. 定义 `vocabulary` 索引的 mappings：字段包括 `word` (text + keyword), `definition` (text), `language` (keyword), `tags` (keyword)
3. 实现 `VocabularySearcher`：
   - `ensure_index()`: 检查并创建索引
   - `index_document(doc)`: 写入文档
   - `search(query, fuzzy=True, expand_synonyms=True)`: 使用 `multi_match` + `fuzziness: AUTO`
4. 在 `scripts/` 下新增 `init_es_index.py`，作为初始化脚本
5. 在 `docker-compose.dev.yml` 中为 ES 增加 `xpack.security.enabled=false`（已配置）

**技术选型**: `elasticsearch[async]>=8.11`

**配置示例**:
```python
# backend_fastapi/app/infrastructure/persistence/search/es_client.py
from elasticsearch import AsyncElasticsearch

es = AsyncElasticsearch(["http://localhost:9200"])

INDEX_NAME = "aifl_vocabulary"

MAPPINGS = {
    "properties": {
        "word": {"type": "text", "analyzer": "standard", "fields": {"keyword": {"type": "keyword"}}},
        "definition": {"type": "text"},
        "language": {"type": "keyword"},
        "tags": {"type": "keyword"},
    }
}

async def ensure_index() -> None:
    if not await es.indices.exists(index=INDEX_NAME):
        await es.indices.create(index=INDEX_NAME, mappings=MAPPINGS)

async def search_vocabulary(query: str, fuzzy: bool = True, size: int = 20) -> list[dict]:
    q = {
        "multi_match": {
            "query": query,
            "fields": ["word^3", "definition", "tags"],
            "fuzziness": "AUTO" if fuzzy else "0",
        }
    }
    resp = await es.search(index=INDEX_NAME, query=q, size=size)
    return [hit["_source"] for hit in resp["hits"]["hits"]]
```

---

### 3.4 消息队列层

**现状**: RabbitMQ 容器和 Celery 配置占位已存在，但缺少实际的 Celery Task 函数、死信队列配置、以及 FastAPI 投递任务的示例路由。

**目标**: 实现作文批改等异步任务的 Celery Worker，配置死信交换机和重试策略，提供 FastAPI 集成示例。

**方案**:
1. 新建 `app/infrastructure/messaging/tasks.py`，定义实际任务：
   - `grade_essay_task(essay_id: str, content: str)` → 投递到 `urgent_tasks`
   - `generate_daily_vocab_task(user_id: str)` → 投递到 `default_tasks`
2. 在 `celery_app.py` 中补充死信交换机 (DLX) 和死信队列 (DLQ) 配置：
   - 为每个业务队列设置 `x-dead-letter-exchange`
   - 任务失败 3 次后进入 DLQ
3. 新建 `app/interfaces/tasks_router.py`，提供 `POST /api/v1/tasks/essay` 接口，演示如何从 FastAPI 投递 Celery 任务
4. 补充 `tests/test_celery_tasks.py`，使用 `CELERY_DEMO_EAGER=1` 做同步测试

**技术选型**: `celery>=5.3`, `kombu`, `rabbitmq:3.12-management`

**配置示例**:
```python
# backend_fastapi/app/infrastructure/messaging/celery_app.py
from celery import Celery
from kombu import Exchange, Queue

broker_url = "amqp://guest:guest@localhost:5672//"
result_backend = "redis://localhost:6379/0"

dlx = Exchange("dlx", type="direct")
dlq = Queue("dlq", exchange=dlx, routing_key="dlq")

queue_args = {
    "x-max-priority": 10,
    "x-dead-letter-exchange": "dlx",
    "x-dead-letter-routing-key": "dlq",
}

task_queues = (
    Queue("urgent_tasks", Exchange("urgent"), routing_key="urgent.#", queue_arguments=queue_args),
    Queue("default_tasks", Exchange("default"), routing_key="default.#", queue_arguments=queue_args),
    Queue("batch_tasks", Exchange("batch"), routing_key="batch.#", queue_arguments=queue_args),
)

app = Celery("aifl_tasks", broker=broker_url, backend=result_backend)
app.conf.update(
    task_queues=task_queues + (dlq,),
    task_default_queue="default_tasks",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_retry_backoff=True,
    task_retry_max_retries=3,
)
```

```python
# backend_fastapi/app/infrastructure/messaging/tasks.py
from .celery_app import app

@app.task(bind=True, max_retries=3)
def grade_essay_task(self, essay_id: str, content: str) -> dict:
    try:
        # 调用现有 essay grading 逻辑
        result = {"essay_id": essay_id, "score": 85, "feedback": "Good job!"}
        return result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
```

---

### 3.5 文件存储层

**现状**: MinIO 容器已就绪，`FileStorage` Protocol 已定义，但无具体实现类和 FastAPI 上传路由。

**目标**: 实现 MinIO 客户端封装，提供文件上传、分片上传、预签名 URL 生成，并在 FastAPI 中注册上传路由。

**方案**:
1. 新建 `app/infrastructure/storage/minio_storage.py`，封装 `minio.Minio` 异步操作（使用 `minio` 官方 SDK 的同步接口在线程池中执行）
2. 实现 `MinIOStorage` 类：
   - `upload(bucket, key, data)` → 自动创建 bucket
   - `initiate_multipart_upload(bucket, key)` → 返回 upload_id
   - `complete_multipart_upload(...)` → 完成分片
   - `generate_presigned_url(bucket, key, expires)` → 返回临时访问 URL
3. 新建 `app/interfaces/storage_router.py`，提供：
   - `POST /api/v1/upload` → 单文件上传
   - `POST /api/v1/upload/multipart/init` → 初始化分片上传
   - `POST /api/v1/upload/multipart/complete` → 完成分片上传
4. 补充 `tests/test_minio_storage.py`

**技术选型**: `minio>=7.2`

**配置示例**:
```python
# backend_fastapi/app/infrastructure/storage/minio_storage.py
import asyncio
from dataclasses import dataclass
from minio import Minio

@dataclass
class UploadResult:
    bucket: str
    object_key: str
    etag: str
    presigned_url: str | None = None

class MinIOStorage:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, secure: bool = False):
        self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)

    async def upload(self, bucket: str, key: str, data: bytes) -> UploadResult:
        loop = asyncio.get_event_loop()
        if not await loop.run_in_executor(None, self.client.bucket_exists, bucket):
            await loop.run_in_executor(None, self.client.make_bucket, bucket)
        result = await loop.run_in_executor(
            None, self.client.put_object, bucket, key, data, len(data)
        )
        return UploadResult(bucket=bucket, object_key=key, etag=result.etag)

    async def generate_presigned_url(self, bucket: str, key: str, expires: int = 3600) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.client.presigned_get_object, bucket, key, expires
        )
```

---

### 3.6 监控可观测性

**现状**: Prometheus 指标收集器和 `/metrics` 端点已存在，`TraceMiddleware` 已定义，但未实际挂载到 FastAPI 中间件栈，请求指标无法自动采集。无 ELK/Grafana/ClickHouse。

**目标**: 将 `TraceMiddleware` 和指标采集挂载到请求链路，统一日志格式，建立最小可用可观测性体系。

**方案**:
1. 在 `app/main.py` 中注册自定义中间件，在请求进入时调用 `TraceMiddleware.process_request()`，在请求结束时自动调用 `PrometheusMetricsCollector` 记录延迟和状态码
2. 统一日志输出为 JSON：当前 `structlog` 已配置，确保所有路由通过 `structlog.get_logger()` 打印日志
3. 在日志中自动注入 `trace_id` 和 `request_id`：通过 `tracing.py` 的 `contextvars` 获取并在 `structlog` 的 processor 中绑定
4. 延后 ELK/Grafana/ClickHouse：当前阶段仅保留 Prometheus + JSON 日志基线，待后续阶段再扩展

**技术选型**: `prometheus-client`, `structlog`, `contextvars`

**配置示例**:
```python
# backend_fastapi/app/main.py (中间件片段)
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.infrastructure.telemetry.tracing import TraceMiddleware, get_trace_id, get_request_id
from app.infrastructure.telemetry.metrics import get_metrics_collector
import time

class TelemetryMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tracer = TraceMiddleware()
        await tracer.process_request(request)
        start = time.time()
        response: Response = await call_next(request)
        duration_ms = (time.time() - start) * 1000
        metrics = get_metrics_collector()
        metrics.increment_request_count(request.method, request.url.path, response.status_code)
        metrics.observe_request_latency(request.method, request.url.path, duration_ms)
        response.headers["X-Trace-Id"] = get_trace_id()
        response.headers["X-Request-Id"] = get_request_id()
        return response

# 在 app = FastAPI(...) 后注册
app.add_middleware(TelemetryMiddleware)
```

---

### 3.7 部署运维

**现状**: `docker-compose.dev.yml` 和 `docker-compose.infra.yml` 已分别编排开发和基础设施服务，但缺少统一的本地部署脚本、环境变量模板说明、以及健康检查汇总。

**目标**: 提供一键启动脚本、完整的环境变量说明、以及本地 PC 部署优化建议。

**方案**:
1. 新建 `backend_fastapi/scripts/start_infra.py`：自动按顺序启动 `docker-compose.dev.yml` 和 `docker-compose.infra.yml`，并轮询等待所有服务健康检查通过
2. 完善 `.env.example`，增加所有基础设施相关的环境变量：
   - `DATABASE_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
   - `REDIS_URL`, `ES_URL`, `NEO4J_URL`, `MINIO_ENDPOINT`
   - `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`
3. 针对本地 PC（AMD 9950X3D + RTX 5080）优化：
   - ES 内存限制为 `-Xms1g -Xmx1g`（已配置）
   - Neo4j 无需额外 JVM 调优，Community 版已足够
   - 所有容器使用 `restart: unless-stopped`，避免系统重启后手动恢复
4. 延后 K8s：本地部署以 Docker Compose 为唯一方案，不引入 K8s 复杂度

**技术选型**: Docker Compose, Python 脚本

**配置示例**:
```python
# backend_fastapi/scripts/start_infra.py
import subprocess
import sys
import time

def run(cmd: list[str]) -> None:
    print("$ " + " ".join(cmd))
    subprocess.run(cmd, check=True)

def wait_for_postgres():
    for i in range(30):
        try:
            import psycopg2
            psycopg2.connect("host=localhost port=5432 dbname=aifl_db user=aifl_user password=aifl_password").close()
            print("PostgreSQL is ready.")
            return
        except Exception:
            time.sleep(1)
    sys.exit("PostgreSQL did not become ready in time.")

if __name__ == "__main__":
    run(["docker", "compose", "-f", "docker-compose.dev.yml", "up", "-d"])
    run(["docker", "compose", "-f", "docker-compose.infra.yml", "up", "-d"])
    wait_for_postgres()
    print("All infrastructure services are up.")
```

---

## 4. 实施路线图

```
Phase 3.1: 数据库层 (Alembic + 异步连接池) → 8工时
Phase 3.2: 缓存层 (分布式锁 + Cache-Aside + 降级) → 4工时
Phase 3.3: 搜索层 (ES 索引 + VocabularySearcher 实现) → 6工时
Phase 3.4: 消息队列层 (Celery tasks + DLQ + FastAPI 路由) → 8工时
Phase 3.5: 文件存储层 (MinIO 封装 + 上传路由 + 预签名 URL) → 6工时
Phase 3.6: 监控可观测性 (TelemetryMiddleware + 日志注入) → 4工时
Phase 3.7: 部署运维 (统一启动脚本 + .env 文档) → 2工时
```

**总估算工时**: 38工时

---

## 5. 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 异步数据库迁移引入兼容性问题（Session 改为 AsyncSession） | 高 | 高 | 分阶段迁移：先新增 `get_async_session()`，保留原同步接口，逐步替换路由 |
| ES 8.11 与 `elasticsearch[async]` 版本兼容性 | 低 | 中 | 使用与容器相同版本的 Python 客户端，并在集成测试中验证 |
| RabbitMQ 死信队列配置复杂，Celery 重试与 DLQ 行为冲突 | 中 | 中 | 先在小范围任务（如 `generate_daily_vocab_task`）上验证，再推广到作文批改 |
| MinIO 预签名 URL 在本地网络外无法访问 | 中 | 低 | 本地部署场景下预签名 URL 仅供同一局域网使用；如需外网，配置反向代理 |
| 成员2历史交付物为空，重构工作量大 | 高 | 高 | 不直接复用成员2代码，按本方案从头实现，并补充完整测试和文档 |
| 本地 PC 同时运行多个容器导致内存不足 | 中 | 高 | ES 限制 1GB JVM，其他服务使用 Alpine 镜像；必要时关闭暂时不用的服务 |

---

## 6. 验收标准

- [ ] `alembic upgrade head` 能成功创建/更新所有表结构
- [ ] `pytest tests/infrastructure/persistence/` 全部通过（含 Redis 缓存、ES 搜索测试）
- [ ] `pytest tests/infrastructure/messaging/` 全部通过（含 Celery 任务投递和消费测试）
- [ ] `pytest tests/infrastructure/storage/` 全部通过（含 MinIO 上传和预签名 URL 测试）
- [ ] `POST /api/v1/tasks/essay` 能成功投递异步任务，Worker 在 10 秒内消费完成
- [ ] `POST /api/v1/upload` 能成功上传文件到 MinIO，并返回可访问的预签名 URL
- [ ] `/metrics` 端点返回的请求总数和延迟分位数随 API 调用实时增加
- [ ] 所有日志条目包含 `trace_id` 和 `request_id`
- [ ] `python scripts/start_infra.py` 能一键启动所有基础设施服务并等待就绪

---

## 7. 下一步建议

1. **立即启动 Phase 3.1（数据库层）**: 初始化 Alembic 并生成首个迁移脚本，这是所有后续模块的 schema 基座
2. **并行启动 Phase 3.4（消息队列）和 Phase 3.5（文件存储）**: 这两项是成员2的核心缺口，填充后可使作文批改和文件上传功能真正可用
3. **为成员6设定明确的监控基线目标**: 当前阶段只要求 Prometheus `/metrics` + TraceID 中间件 + JSON 日志，ClickHouse/ELK/Grafana 明确延后到下一阶段
4. **在本地 PC 上运行 `start_infra.py` 做端到端验证**: 确保 PostgreSQL、Redis、ES、Neo4j、RabbitMQ、MinIO 能同时稳定运行，根据实际内存占用调整 ES JVM 参数
5. **建立基础设施变更的 Code Review 标准**: 所有涉及 Docker Compose、数据库迁移、消息队列配置的 PR 必须经过双人 Review，防止配置错误导致数据丢失或服务中断

---

# Agent 执行结果汇总：基础设施工程师

**执行日期**: 2026年4月12日  
**执行范围**: Phase 3.1 ~ 3.7 全部  
**执行状态**: 代码已完成，单元测试通过；Docker 端到端验证因本地网络拉取镜像超时未能完成

---

## 执行摘要

- **新增配置文件**: 1（`.env.example` 扩充）
- **新增/修改代码文件**: 17
- **新增运维脚本**: 1（`scripts/start_infra.py`）
- **新增监控配置**: 已集成（TelemetryMiddleware + Prometheus 指标自动采集）
- **新增 Alembic 迁移**: 1（`5151f4ec6575_initial_migration.py`，覆盖 10 张表）
- **新增测试文件**: 3（Redis 缓存、ES 搜索、Celery 任务）
- **单元测试通过**: 6/6
- **Docker 服务启动验证**: 未通过（本地无法拉取 Docker Hub 镜像）
- **文档更新**: 是（`.env.example` 已补充完整环境变量说明）

---

## 配置清单

### 1. Docker Compose 服务（已存在，未修改）

| 服务 | 版本 | 端口 | 状态 |
|------|------|------|------|
| PostgreSQL | 16-alpine | 5432 | 已配置（健康检查已存在） |
| Redis | 7-alpine | 6379 | 已配置（健康检查已存在） |
| Elasticsearch | 8.11.0 | 9200/9300 | 已配置（健康检查已存在） |
| Neo4j | 5.15-community | 7474/7687 | 已配置 |
| RabbitMQ | 3.12-management | 5672/15672 | 已配置（健康检查已存在） |
| MinIO | latest | 9000/9001 | 已配置（健康检查已存在） |

### 2. Python 客户端封装

| 服务 | 文件路径 | 状态 |
|------|----------|------|
| PostgreSQL 异步连接池 | `backend_fastapi/app/db.py` | 已完成 |
| Redis 缓存 + 分布式锁 | `backend_fastapi/app/infrastructure/persistence/cache/redis_cache.py` | 已完成 |
| Elasticsearch 搜索 | `backend_fastapi/app/infrastructure/persistence/search/es_client.py` | 已完成 |
| Celery 应用 + DLQ | `backend_fastapi/app/infrastructure/messaging/celery_app.py` | 已完成 |
| Celery 任务函数 | `backend_fastapi/app/infrastructure/messaging/tasks.py` | 已完成 |
| MinIO 存储封装 | `backend_fastapi/app/infrastructure/storage/minio_storage.py` | 已完成 |

### 3. FastAPI 路由

| 路由 | 文件路径 | 状态 |
|------|----------|------|
| 任务投递路由 | `backend_fastapi/app/interfaces/tasks_router.py` | 已完成 |
| 文件上传路由 | `backend_fastapi/app/interfaces/storage_router.py` | 已完成 |
| 可观测性中间件 | `backend_fastapi/app/main.py` (telemetry_middleware) | 已完成 |

### 4. 运维脚本

| 脚本 | 功能 | 路径 | 状态 |
|------|------|------|------|
| `start_infra.py` | 一键启动 dev + infra 的 Docker Compose，并轮询等待 PostgreSQL/Redis/ES/RabbitMQ/MinIO 就绪 | `backend_fastapi/scripts/start_infra.py` | 已完成 |

### 5. 监控配置

| 配置 | 路径 | 状态 |
|------|------|------|
| Prometheus 指标自动采集 | `backend_fastapi/app/main.py` | 已完成 |
| TraceID / RequestID 注入 | `backend_fastapi/app/main.py` | 已完成 |
| JSON 结构化日志 | `backend_fastapi/app/logging.py`（已存在） | 已兼容 |

### 6. 测试覆盖

| 测试文件 | 测试内容 | 结果 |
|----------|----------|------|
| `tests/test_redis_cache.py` | Redis 降级、Cache-Aside | 2 passed |
| `tests/test_es_search.py` | VocabularySearcher 返回列表 | 2 passed |
| `tests/test_celery_tasks.py` | Celery eager 模式任务执行 | 2 passed |

---

## 关键配置示例

### Alembic 异步 env.py（SQLite 回退）

```python
# backend_fastapi/alembic/env.py
def run_migrations_online() -> None:
    url = config.get_main_option("sqlalchemy.url")
    if url.startswith("sqlite"):
        from sqlalchemy import create_engine
        connectable = create_engine(url, poolclass=pool.NullPool)
        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    else:
        asyncio.run(run_async_migrations())
```

### 异步数据库引擎配置

```python
# backend_fastapi/app/db.py
engine = create_async_engine(
    url,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
)
```

### Celery DLQ 配置

```python
# backend_fastapi/app/infrastructure/messaging/celery_app.py
queue_args = {
    "x-max-priority": 10,
    "x-dead-letter-exchange": "dlx",
    "x-dead-letter-routing-key": "dlq",
}
task_queues = (
    Queue("urgent_tasks", ...),
    Queue("default_tasks", ...),
    Queue("batch_tasks", ...),
    dlq,
)
```

### Telemetry 中间件

```python
# backend_fastapi/app/main.py
async def telemetry_middleware(request, call_next):
    tracer = TraceMiddleware()
    await tracer.process_request(request)
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    metrics = get_metrics_collector()
    metrics.increment_request_count(...)
    metrics.observe_request_latency(...)
    response.headers["X-Trace-Id"] = get_trace_id()
    response.headers["X-Request-Id"] = get_request_id()
    return response

app.middleware("http")(telemetry_middleware)
```

---

## 服务验证结果

### 单元测试

```
tests/test_redis_cache.py ..   (2 passed)
tests/test_es_search.py    ..   (2 passed)
tests/test_celery_tasks.py ..   (2 passed)
```

### FastAPI 应用导入

```
FastAPI app imported successfully
```

### Docker Compose 启动

```
# 因本地网络无法连接 Docker Hub，镜像拉取超时，未能完成容器启动验证。
# 建议在网络畅通后执行：
#   python backend_fastapi/scripts/start_infra.py
```

---

## 遇到的问题与解决方案

1. **问题**: `pip install -e ".[dev]"` 失败，提示 `Multiple top-level packages discovered`
   **解决**: 在 `pyproject.toml` 中增加 `[tool.setuptools] packages = ["app"]` 显式声明包名

2. **问题**: Alembic 使用 SQLite 生成迁移时，`async_engine_from_config` 报错 `pysqlite is not async`
   **解决**: 在 `env.py` 的 `run_migrations_online()` 中增加 SQLite 同步引擎回退分支

3. **问题**: `storage_router.py` 使用 `UploadFile` 时 FastAPI 报错缺少 `python-multipart`
   **解决**: 执行 `pip install python-multipart`

4. **问题**: 本地 Docker 无法拉取镜像（`request canceled while waiting for connection`）
   **解决**: 记录为环境阻塞，代码层面已完成所有健康检查和启动脚本，待网络恢复后可直接运行 `start_infra.py`

---

## 未完成任务

1. **Docker 容器端到端验证** — 本地网络无法拉取 Docker Hub 镜像，阻塞原因：网络超时
2. **Alembic `upgrade head` 在 PostgreSQL 上执行** — 需等待 PostgreSQL 容器启动后方可验证

---

## 下一步建议

1. **恢复 Docker 网络环境后，立即运行 `python scripts/start_infra.py`**，验证所有基础设施服务健康检查通过
2. **在 PostgreSQL 就绪后执行 `alembic upgrade head`**，确认迁移脚本能在真实 PostgreSQL 上成功执行
3. **补充 MinIO 和消息队列的集成测试**：待容器启动后，运行上传路由和任务投递路由的端到端测试
4. **将 `python-multipart` 加入 `pyproject.toml` 依赖列表**，避免后续环境缺失
5. **评估是否引入 `aiosqlite`**：若未来需要 SQLite 的完全异步支持，可替换 `sqlite` 为 `sqlite+aiosqlite`

