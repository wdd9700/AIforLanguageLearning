# =====================================================
# AI外语学习系统 - Elasticsearch 客户端
# 版本: 1.0.0
# 描述: Elasticsearch异步客户端连接和索引管理
# =====================================================

import logging
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

try:
    from elasticsearch import AsyncElasticsearch
    from elasticsearch.exceptions import NotFoundError, ConnectionError as ESConnectionError
    ES_AVAILABLE = True
except ImportError:
    ES_AVAILABLE = False
    AsyncElasticsearch = None

from .es_config import (
    VOCABULARY_INDEX_MAPPING,
    SYNONYM_INDEX_MAPPING,
    SUGGESTION_INDEX_MAPPING,
    INDEX_NAMES,
    SEARCH_CONFIG
)

logger = logging.getLogger(__name__)


class ElasticsearchClient:
    """
    Elasticsearch异步客户端
    
    功能：
    1. 连接管理（连接、关闭、健康检查）
    2. 索引管理（创建、删除、更新映射）
    3. 文档操作（索引、批量索引、删除）
    4. 搜索功能（查询、建议、同义词）
    """
    
    def __init__(
        self,
        hosts: Optional[List[str]] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_certs: bool = False,
        **kwargs
    ):
        """
        初始化ES客户端
        
        Args:
            hosts: ES主机列表，默认 ["http://localhost:9200"]
            username: 用户名（如果需要认证）
            password: 密码（如果需要认证）
            verify_certs: 是否验证SSL证书
            **kwargs: 其他ES客户端参数
        """
        if not ES_AVAILABLE:
            raise ImportError("elasticsearch package is not installed. "
                            "Install it with: pip install elasticsearch[async]")
        
        self.hosts = hosts or ["http://localhost:9200"]
        self.username = username
        self.password = password
        self.verify_certs = verify_certs
        self.kwargs = kwargs
        self.client: Optional[AsyncElasticsearch] = None
        self._connected = False
    
    async def connect(self) -> bool:
        """
        连接到Elasticsearch
        
        Returns:
            是否连接成功
        """
        try:
            auth = None
            if self.username and self.password:
                auth = (self.username, self.password)
            
            self.client = AsyncElasticsearch(
                hosts=self.hosts,
                basic_auth=auth,
                verify_certs=self.verify_certs,
                **self.kwargs
            )
            
            # 测试连接
            info = await self.client.info()
            logger.info(f"Connected to Elasticsearch {info['version']['number']}")
            self._connected = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {e}")
            self._connected = False
            return False
    
    async def close(self):
        """关闭连接"""
        if self.client:
            await self.client.close()
            self._connected = False
            logger.info("Elasticsearch connection closed")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            集群健康状态
        """
        if not self.client:
            return {"status": "disconnected"}
        
        try:
            health = await self.client.cluster.health()
            return {
                "status": health["status"],
                "cluster_name": health["cluster_name"],
                "number_of_nodes": health["number_of_nodes"],
                "active_shards": health["active_shards"],
                "unassigned_shards": health["unassigned_shards"]
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "error": str(e)}
    
    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._connected and self.client is not None
    
    # -------------------------------------------------
    # 索引管理
    # -------------------------------------------------
    
    async def index_exists(self, index_name: str) -> bool:
        """
        检查索引是否存在
        
        Args:
            index_name: 索引名称
            
        Returns:
            是否存在
        """
        if not self.client:
            return False
        return await self.client.indices.exists(index=index_name)
    
    async def create_index(
        self,
        index_name: str,
        mapping: Optional[Dict[str, Any]] = None,
        ignore_existing: bool = True
    ) -> bool:
        """
        创建索引
        
        Args:
            index_name: 索引名称
            mapping: 索引映射配置
            ignore_existing: 如果索引已存在是否忽略
            
        Returns:
            是否创建成功
        """
        if not self.client:
            logger.error("Elasticsearch client not connected")
            return False
        
        try:
            exists = await self.index_exists(index_name)
            if exists:
                if ignore_existing:
                    logger.info(f"Index '{index_name}' already exists")
                    return True
                else:
                    logger.warning(f"Index '{index_name}' already exists")
                    return False
            
            body = mapping or {}
            await self.client.indices.create(index=index_name, body=body)
            logger.info(f"Created index: {index_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create index {index_name}: {e}")
            return False
    
    async def delete_index(self, index_name: str, ignore_missing: bool = True) -> bool:
        """
        删除索引
        
        Args:
            index_name: 索引名称
            ignore_missing: 如果索引不存在是否忽略
            
        Returns:
            是否删除成功
        """
        if not self.client:
            return False
        
        try:
            await self.client.indices.delete(
                index=index_name,
                ignore_unavailable=ignore_missing
            )
            logger.info(f"Deleted index: {index_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete index {index_name}: {e}")
            return False
    
    async def init_indices(self) -> Dict[str, bool]:
        """
        初始化所有索引
        
        Returns:
            各索引创建结果
        """
        results = {}
        
        # 词汇索引
        results["vocabulary"] = await self.create_index(
            INDEX_NAMES["vocabulary"],
            VOCABULARY_INDEX_MAPPING
        )
        
        # 同义词索引
        results["synonyms"] = await self.create_index(
            INDEX_NAMES["synonyms"],
            SYNONYM_INDEX_MAPPING
        )
        
        # 搜索建议索引
        results["suggestions"] = await self.create_index(
            INDEX_NAMES["suggestions"],
            SUGGESTION_INDEX_MAPPING
        )
        
        return results
    
    async def get_mapping(self, index_name: str) -> Optional[Dict[str, Any]]:
        """
        获取索引映射
        
        Args:
            index_name: 索引名称
            
        Returns:
            映射配置
        """
        if not self.client:
            return None
        
        try:
            mapping = await self.client.indices.get_mapping(index=index_name)
            return mapping.get(index_name, {}).get("mappings", {})
        except Exception as e:
            logger.error(f"Failed to get mapping for {index_name}: {e}")
            return None
    
    # -------------------------------------------------
    # 文档操作
    # -------------------------------------------------
    
    async def index_document(
        self,
        index_name: str,
        document: Dict[str, Any],
        doc_id: Optional[str] = None
    ) -> bool:
        """
        索引单个文档
        
        Args:
            index_name: 索引名称
            document: 文档内容
            doc_id: 文档ID（可选）
            
        Returns:
            是否索引成功
        """
        if not self.client:
            return False
        
        try:
            await self.client.index(
                index=index_name,
                id=doc_id,
                document=document
            )
            return True
        except Exception as e:
            logger.error(f"Failed to index document: {e}")
            return False
    
    async def bulk_index(
        self,
        index_name: str,
        documents: List[Dict[str, Any]],
        id_field: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        批量索引文档
        
        Args:
            index_name: 索引名称
            documents: 文档列表
            id_field: 用作ID的字段名
            
        Returns:
            批量操作结果
        """
        if not self.client:
            return {"success": False, "error": "Client not connected"}
        
        if not documents:
            return {"success": True, "indexed": 0, "errors": []}
        
        try:
            from elasticsearch.helpers import async_bulk
            
            def generate_actions():
                for doc in documents:
                    action = {
                        "_index": index_name,
                        "_source": doc
                    }
                    if id_field and id_field in doc:
                        action["_id"] = doc[id_field]
                    yield action
            
            success, errors = await async_bulk(
                self.client,
                generate_actions(),
                raise_on_error=False
            )
            
            return {
                "success": True,
                "indexed": success,
                "errors": errors if isinstance(errors, list) else []
            }
            
        except Exception as e:
            logger.error(f"Bulk index failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def delete_document(self, index_name: str, doc_id: str) -> bool:
        """
        删除文档
        
        Args:
            index_name: 索引名称
            doc_id: 文档ID
            
        Returns:
            是否删除成功
        """
        if not self.client:
            return False
        
        try:
            await self.client.delete(index=index_name, id=doc_id)
            return True
        except NotFoundError:
            logger.warning(f"Document {doc_id} not found in {index_name}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False
    
    async def get_document(
        self,
        index_name: str,
        doc_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取文档
        
        Args:
            index_name: 索引名称
            doc_id: 文档ID
            
        Returns:
            文档内容
        """
        if not self.client:
            return None
        
        try:
            result = await self.client.get(index=index_name, id=doc_id)
            return result.get("_source")
        except NotFoundError:
            return None
        except Exception as e:
            logger.error(f"Failed to get document: {e}")
            return None
    
    # -------------------------------------------------
    # 搜索功能
    # -------------------------------------------------
    
    async def search(
        self,
        index_name: str,
        query: Dict[str, Any],
        size: int = 20,
        from_offset: int = 0,
        sort: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        执行搜索
        
        Args:
            index_name: 索引名称
            query: ES查询DSL
            size: 返回结果数
            from_offset: 分页偏移
            sort: 排序规则
            
        Returns:
            搜索结果
        """
        if not self.client:
            return {"hits": {"hits": [], "total": {"value": 0}}}
        
        try:
            body = {"query": query}
            if sort:
                body["sort"] = sort
            
            response = await self.client.search(
                index=index_name,
                body=body,
                size=size,
                from_=from_offset
            )
            return response
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {"hits": {"hits": [], "total": {"value": 0}}, "error": str(e)}
    
    async def suggest(
        self,
        index_name: str,
        field: str,
        prefix: str,
        size: int = 10
    ) -> List[str]:
        """
        获取搜索建议
        
        Args:
            index_name: 索引名称
            field: 建议字段
            prefix: 输入前缀
            size: 返回数量
            
        Returns:
            建议列表
        """
        if not self.client:
            return []
        
        try:
            response = await self.client.search(
                index=index_name,
                body={
                    "suggest": {
                        "suggestions": {
                            "prefix": prefix,
                            "completion": {
                                "field": field,
                                "size": size,
                                "fuzzy": {"fuzziness": "AUTO"}
                            }
                        }
                    }
                }
            )
            
            suggestions = response.get("suggest", {}).get("suggestions", [{}])[0]
            options = suggestions.get("options", [])
            return [opt["text"] for opt in options]
            
        except Exception as e:
            logger.error(f"Suggest failed: {e}")
            return []


# 便捷函数
async def get_es_client(
    hosts: Optional[List[str]] = None,
    **kwargs
) -> ElasticsearchClient:
    """
    获取ES客户端实例并连接
    
    Args:
        hosts: ES主机列表
        **kwargs: 其他参数
        
    Returns:
        已连接的ES客户端
    """
    client = ElasticsearchClient(hosts=hosts, **kwargs)
    await client.connect()
    return client


@asynccontextmanager
async def es_client_context(**kwargs):
    """
    ES客户端上下文管理器
    
    Usage:
        async with es_client_context() as client:
            await client.search(...)
    """
    client = ElasticsearchClient(**kwargs)
    try:
        await client.connect()
        yield client
    finally:
        await client.close()
