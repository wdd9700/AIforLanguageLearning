# =====================================================
# AI外语学习系统 - 词汇搜索API
# 版本: 1.0.0
# 描述: 提供词汇搜索、建议、同义词等REST API接口
# =====================================================

import logging
from typing import List, Dict, Any, Optional
from dataclasses import asdict

try:
    from fastapi import APIRouter, HTTPException, Query
    from fastapi.responses import JSONResponse
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    APIRouter = None

from ..search.vocabulary_search import VocabularySearcher, VocabularySearchResult
from ..search.vocabulary_indexer import VocabularyIndexer, VocabularyEntry
from ..search.es_client import ElasticsearchClient

logger = logging.getLogger(__name__)

# 创建路由
if FASTAPI_AVAILABLE:
    router = APIRouter(prefix="/vocabulary", tags=["vocabulary"])
else:
    router = None


class VocabularySearchService:
    """
    词汇搜索服务
    
    封装搜索功能，提供统一的API接口
    """
    
    def __init__(
        self,
        es_client: Optional[ElasticsearchClient] = None,
        redis_client=None
    ):
        self.es_client = es_client
        self.redis_client = redis_client
        self.searcher = VocabularySearcher(
            es_client=es_client,
            redis_client=redis_client
        )
        self.indexer = VocabularyIndexer(es_client=es_client)
    
    async def search(
        self,
        query: str,
        fuzzy: bool = True,
        expand_synonyms: bool = True,
        language: str = "en",
        difficulty: Optional[int] = None,
        part_of_speech: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        搜索词汇
        
        Args:
            query: 搜索关键词
            fuzzy: 是否启用模糊搜索
            expand_synonyms: 是否扩展同义词
            language: 词汇语言
            difficulty: 难度等级过滤
            part_of_speech: 词性过滤
            tags: 标签过滤
            limit: 返回结果数
            offset: 分页偏移
            
        Returns:
            搜索结果
        """
        # 构建过滤条件
        filters = {}
        if difficulty is not None:
            filters["difficulty_level"] = difficulty
        if part_of_speech:
            filters["part_of_speech"] = part_of_speech
        if tags:
            filters["tags"] = tags
        if language:
            filters["language"] = language
        
        # 执行搜索
        results = await self.searcher.search(
            query=query,
            fuzzy=fuzzy,
            expand_synonyms=expand_synonyms,
            language=language,
            filters=filters if filters else None,
            size=limit,
            from_offset=offset
        )
        
        return {
            "query": query,
            "count": len(results),
            "results": [r.to_dict() for r in results]
        }
    
    async def get_suggestions(
        self,
        prefix: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        获取搜索建议
        
        Args:
            prefix: 输入前缀
            limit: 返回建议数
            
        Returns:
            建议列表
        """
        suggestions = await self.searcher.get_suggestions(prefix, limit)
        return {
            "prefix": prefix,
            "suggestions": suggestions
        }
    
    async def get_synonyms(
        self,
        word: str
    ) -> Dict[str, Any]:
        """
        获取同义词
        
        Args:
            word: 查询词汇
            
        Returns:
            同义词列表
        """
        synonyms = await self.searcher.get_synonyms(word)
        return {
            "word": word,
            "synonyms": synonyms,
            "count": len(synonyms)
        }
    
    async def spell_check(
        self,
        word: str
    ) -> Dict[str, Any]:
        """
        拼写检查
        
        Args:
            word: 待检查词汇
            
        Returns:
            拼写建议
        """
        corrections = await self.searcher.spell_check(word)
        return {
            "word": word,
            "corrections": corrections,
            "has_correction": len(corrections) > 0
        }
    
    async def index_vocabulary(
        self,
        entry: VocabularyEntry
    ) -> Dict[str, Any]:
        """
        索引词汇
        
        Args:
            entry: 词汇条目
            
        Returns:
            索引结果
        """
        success = await self.indexer.index_vocabulary(entry)
        return {
            "success": success,
            "word": entry.word,
            "id": entry.id
        }
    
    async def bulk_index(
        self,
        entries: List[VocabularyEntry]
    ) -> Dict[str, Any]:
        """
        批量索引词汇
        
        Args:
            entries: 词汇条目列表
            
        Returns:
            批量索引结果
        """
        result = await self.indexer.bulk_index_vocabulary(entries)
        return result


# =====================================================
# FastAPI路由定义
# =====================================================

if FASTAPI_AVAILABLE:
    
    # 服务实例（将在应用启动时初始化）
    search_service: Optional[VocabularySearchService] = None
    
    def init_service(es_client: ElasticsearchClient, redis_client=None):
        """初始化搜索服务"""
        global search_service
        search_service = VocabularySearchService(
            es_client=es_client,
            redis_client=redis_client
        )
    
    @router.get("/search")
    async def search_vocabulary(
        q: str = Query(..., description="搜索关键词"),
        fuzzy: bool = Query(True, description="启用模糊搜索"),
        synonyms: bool = Query(True, description="扩展同义词"),
        language: str = Query("en", description="词汇语言"),
        difficulty: Optional[int] = Query(None, description="难度等级过滤"),
        pos: Optional[str] = Query(None, description="词性过滤"),
        limit: int = Query(20, ge=1, le=100, description="返回结果数"),
        offset: int = Query(0, ge=0, description="分页偏移")
    ):
        """
        搜索词汇
        
        - **q**: 搜索关键词（必需）
        - **fuzzy**: 是否启用模糊搜索（拼写纠错）
        - **synonyms**: 是否扩展同义词
        - **language**: 词汇语言，默认en
        - **difficulty**: 难度等级过滤（1-5）
        - **pos**: 词性过滤（noun, verb, adjective等）
        - **limit**: 返回结果数（1-100）
        - **offset**: 分页偏移
        """
        if not search_service:
            raise HTTPException(status_code=503, detail="Search service not initialized")
        
        try:
            result = await search_service.search(
                query=q,
                fuzzy=fuzzy,
                expand_synonyms=synonyms,
                language=language,
                difficulty=difficulty,
                part_of_speech=pos,
                limit=limit,
                offset=offset
            )
            return result
        except Exception as e:
            logger.error(f"Search error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/suggest")
    async def get_suggestions(
        prefix: str = Query(..., min_length=1, description="输入前缀"),
        limit: int = Query(10, ge=1, le=50, description="返回建议数")
    ):
        """
        获取搜索建议（自动补全）
        
        - **prefix**: 输入前缀（必需）
        - **limit**: 返回建议数（1-50）
        """
        if not search_service:
            raise HTTPException(status_code=503, detail="Search service not initialized")
        
        try:
            return await search_service.get_suggestions(prefix, limit)
        except Exception as e:
            logger.error(f"Suggestions error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/synonyms/{word}")
    async def get_synonyms(word: str):
        """
        获取词汇同义词
        
        - **word**: 查询词汇
        """
        if not search_service:
            raise HTTPException(status_code=503, detail="Search service not initialized")
        
        try:
            return await search_service.get_synonyms(word)
        except Exception as e:
            logger.error(f"Get synonyms error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/spell-check")
    async def spell_check(
        word: str = Query(..., description="待检查词汇")
    ):
        """
        拼写检查
        
        - **word**: 待检查词汇
        
        Example:
            - "restarant" → ["restaurant"]
        """
        if not search_service:
            raise HTTPException(status_code=503, detail="Search service not initialized")
        
        try:
            return await search_service.spell_check(word)
        except Exception as e:
            logger.error(f"Spell check error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/index")
    async def index_vocabulary(entry: Dict[str, Any]):
        """
        索引单个词汇
        
        用于将新词汇添加到搜索引擎
        """
        if not search_service:
            raise HTTPException(status_code=503, detail="Search service not initialized")
        
        try:
            vocab_entry = VocabularyEntry(**entry)
            return await search_service.index_vocabulary(vocab_entry)
        except Exception as e:
            logger.error(f"Index error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/bulk-index")
    async def bulk_index(entries: List[Dict[str, Any]]):
        """
        批量索引词汇
        
        用于批量导入词汇数据
        """
        if not search_service:
            raise HTTPException(status_code=503, detail="Search service not initialized")
        
        try:
            vocab_entries = [VocabularyEntry(**e) for e in entries]
            return await search_service.bulk_index(vocab_entries)
        except Exception as e:
            logger.error(f"Bulk index error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/health")
    async def health_check():
        """健康检查"""
        if not search_service or not search_service.es_client:
            raise HTTPException(status_code=503, detail="Service not available")
        
        health = await search_service.es_client.health_check()
        return {
            "status": "healthy" if health.get("status") in ["green", "yellow"] else "unhealthy",
            "elasticsearch": health
        }


# 便捷函数
async def search_vocabulary_api(
    query: str,
    es_client: ElasticsearchClient,
    **kwargs
) -> Dict[str, Any]:
    """
    搜索词汇API便捷函数
    
    Args:
        query: 搜索关键词
        es_client: ES客户端
        **kwargs: 其他参数
        
    Returns:
        搜索结果
    """
    service = VocabularySearchService(es_client=es_client)
    return await service.search(query, **kwargs)
