# =====================================================
# AI外语学习系统 - 搜索服务层
# 版本: 1.0.0
# 描述: 整合Redis缓存、Elasticsearch和PostgreSQL的多层搜索
# =====================================================

import logging
import json
from typing import List, Dict, Any, Optional
from uuid import UUID
import hashlib

from ..cache.redis_cache import RedisCache
from ..search.vocabulary_search import VocabularySearcher, VocabularySearchResult
from .vocabulary_service import VocabularyService

logger = logging.getLogger(__name__)


class SearchService:
    """
    搜索服务层
    
    整合多层搜索策略：
    1. Redis缓存层 - 快速响应热点查询
    2. Elasticsearch层 - 全文检索、模糊搜索、同义词扩展
    3. PostgreSQL层 - 精确查询、兜底查询
    
    搜索流程：
    Redis缓存 → Elasticsearch → PostgreSQL(兜底)
    """
    
    def __init__(
        self,
        redis_cache: RedisCache,
        es_searcher: VocabularySearcher,
        vocab_service: VocabularyService,
        cache_ttl: int = 300
    ):
        """
        初始化搜索服务
        
        Args:
            redis_cache: Redis缓存客户端
            es_searcher: Elasticsearch搜索器
            vocab_service: 词汇服务
            cache_ttl: 缓存过期时间（秒）
        """
        self.cache = redis_cache
        self.es_searcher = es_searcher
        self.vocab_service = vocab_service
        self.cache_ttl = cache_ttl
    
    def _generate_cache_key(
        self, 
        query: str, 
        fuzzy: bool, 
        expand_synonyms: bool,
        **kwargs
    ) -> str:
        """
        生成缓存键
        
        Args:
            query: 搜索词
            fuzzy: 是否模糊搜索
            expand_synonyms: 是否扩展同义词
            **kwargs: 其他参数
            
        Returns:
            缓存键
        """
        key_data = {
            "query": query.lower().strip(),
            "fuzzy": fuzzy,
            "expand_synonyms": expand_synonyms,
            **kwargs
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return f"search:{hashlib.md5(key_str.encode()).hexdigest()}"
    
    async def search_vocabulary(
        self,
        query: str,
        fuzzy: bool = True,
        expand_synonyms: bool = True,
        language: str = "en",
        use_cache: bool = True,
        size: int = 20
    ) -> Dict[str, Any]:
        """
        搜索词汇（多层搜索）
        
        Args:
            query: 搜索词
            fuzzy: 是否启用模糊搜索（拼写纠错）
            expand_synonyms: 是否扩展同义词
            language: 语言代码
            use_cache: 是否使用缓存
            size: 返回结果数量
            
        Returns:
            搜索结果字典
        """
        result = {
            "query": query,
            "results": [],
            "total": 0,
            "source": None,  # cache, elasticsearch, postgresql
            "time_ms": 0
        }
        
        import time
        start_time = time.time()
        
        # 1. 尝试从Redis缓存获取
        if use_cache:
            cache_key = self._generate_cache_key(
                query, fuzzy, expand_synonyms, language=language
            )
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                result["results"] = cached_result
                result["total"] = len(cached_result)
                result["source"] = "cache"
                result["time_ms"] = int((time.time() - start_time) * 1000)
                logger.info(f"Cache hit for query: {query}")
                return result
        
        # 2. Elasticsearch搜索
        try:
            es_results = await self.es_searcher.search(
                query=query,
                fuzzy=fuzzy,
                expand_synonyms=expand_synonyms,
                language=language,
                size=size
            )
            
            if es_results:
                result["results"] = [r.to_dict() for r in es_results]
                result["total"] = len(es_results)
                result["source"] = "elasticsearch"
                
                # 缓存结果
                if use_cache:
                    await self.cache.set(
                        cache_key, 
                        result["results"], 
                        ttl=self.cache_ttl
                    )
                
                result["time_ms"] = int((time.time() - start_time) * 1000)
                return result
                
        except Exception as e:
            logger.error(f"Elasticsearch search failed: {e}")
        
        # 3. PostgreSQL兜底搜索
        try:
            pg_results = await self.vocab_service.search_vocabulary(
                query=query,
                language=language,
                limit=size
            )
            
            if pg_results:
                result["results"] = pg_results
                result["total"] = len(pg_results)
                result["source"] = "postgresql"
                
                # 缓存结果
                if use_cache:
                    await self.cache.set(
                        cache_key, 
                        result["results"], 
                        ttl=self.cache_ttl
                    )
                
                result["time_ms"] = int((time.time() - start_time) * 1000)
                return result
                
        except Exception as e:
            logger.error(f"PostgreSQL search failed: {e}")
        
        result["time_ms"] = int((time.time() - start_time) * 1000)
        return result
    
    async def get_search_suggestions(
        self,
        query: str,
        language: str = "en",
        size: int = 10
    ) -> List[str]:
        """
        获取搜索建议（自动完成）
        
        Args:
            query: 部分输入
            language: 语言代码
            size: 建议数量
            
        Returns:
            建议列表
        """
        try:
            suggestions = await self.es_searcher.get_suggestions(
                query=query,
                language=language,
                size=size
            )
            return suggestions
        except Exception as e:
            logger.error(f"Failed to get suggestions: {e}")
            return []
    
    async def search_with_synonyms(
        self,
        query: str,
        language: str = "en",
        size: int = 20
    ) -> Dict[str, Any]:
        """
        同义词扩展搜索
        
        示例：搜索 "happy" 会同时返回 "joyful, pleased, cheerful" 等相关词汇
        
        Args:
            query: 搜索词
            language: 语言代码
            size: 返回结果数量
            
        Returns:
            搜索结果（包含同义词）
        """
        result = {
            "query": query,
            "expanded_terms": [],
            "results": [],
            "total": 0,
            "time_ms": 0
        }
        
        import time
        start_time = time.time()
        
        try:
            # 获取同义词扩展
            expanded = await self.es_searcher.expand_synonyms(query)
            result["expanded_terms"] = expanded
            
            # 使用扩展词搜索
            es_results = await self.es_searcher.search(
                query=query,
                fuzzy=False,
                expand_synonyms=True,
                language=language,
                size=size
            )
            
            result["results"] = [r.to_dict() for r in es_results]
            result["total"] = len(es_results)
            result["time_ms"] = int((time.time() - start_time) * 1000)
            
        except Exception as e:
            logger.error(f"Synonym search failed: {e}")
        
        return result
    
    async def fuzzy_search(
        self,
        query: str,
        language: str = "en",
        size: int = 20
    ) -> Dict[str, Any]:
        """
        模糊搜索（拼写纠错）
        
        示例：搜索 "restarant" 能匹配到 "restaurant"
        
        Args:
            query: 搜索词（可能有拼写错误）
            language: 语言代码
            size: 返回结果数量
            
        Returns:
            搜索结果（包含纠错建议）
        """
        result = {
            "query": query,
            "corrected_query": None,
            "results": [],
            "total": 0,
            "time_ms": 0
        }
        
        import time
        start_time = time.time()
        
        try:
            # 尝试模糊搜索
            es_results = await self.es_searcher.search(
                query=query,
                fuzzy=True,
                expand_synonyms=False,
                language=language,
                size=size
            )
            
            if es_results:
                result["results"] = [r.to_dict() for r in es_results]
                result["total"] = len(es_results)
                
                # 如果第一个结果匹配度很高，可能是纠错结果
                if es_results[0].score > 0.8:
                    result["corrected_query"] = es_results[0].word
                    
        except Exception as e:
            logger.error(f"Fuzzy search failed: {e}")
        
        result["time_ms"] = int((time.time() - start_time) * 1000)
        return result
    
    async def get_synonyms_for_word(
        self,
        word: str,
        language: str = "en"
    ) -> List[Dict[str, Any]]:
        """
        获取单词的同义词
        
        Args:
            word: 单词
            language: 语言代码
            
        Returns:
            同义词列表
        """
        # 先获取词汇ID
        vocab = await self.vocab_service.get_vocabulary_by_word(word, language)
        if not vocab:
            return []
        
        # 获取同义词
        synonyms = await self.vocab_service.get_synonyms(UUID(vocab["id"]))
        return synonyms
    
    async def invalidate_search_cache(
        self,
        query_pattern: Optional[str] = None
    ) -> int:
        """
        使搜索缓存失效
        
        Args:
            query_pattern: 查询模式，如果为None则清除所有搜索缓存
            
        Returns:
            清除的缓存数量
        """
        try:
            if query_pattern:
                # 清除特定模式的缓存
                pattern = f"search:*{query_pattern}*"
            else:
                # 清除所有搜索缓存
                pattern = "search:*"
            
            count = await self.cache.delete_pattern(pattern)
            logger.info(f"Invalidated {count} search cache entries")
            return count
            
        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}")
            return 0
