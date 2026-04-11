# =====================================================
# AI外语学习系统 - 词汇搜索模块
# 版本: 1.0.0
# 描述: 提供词汇全文搜索、模糊搜索、同义词扩展等功能
# =====================================================

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
import json
from datetime import datetime

from .es_client import ElasticsearchClient
from .es_config import INDEX_NAMES, SEARCH_CONFIG

# 配置日志
logger = logging.getLogger(__name__)


@dataclass
class VocabularySearchResult:
    """词汇搜索结果数据类"""
    id: str
    word: str
    pronunciation: Optional[str]
    part_of_speech: Optional[str]
    difficulty_level: int
    definition_zh: Optional[str]
    definition_en: Optional[str]
    example_en: Optional[str]
    example_translation_zh: Optional[str]
    tags: List[str]
    synonyms: List[str]
    score: float
    highlights: Dict[str, List[str]]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class VocabularySearcher:
    """
    词汇搜索引擎
    
    提供以下功能：
    1. 精确搜索
    2. 模糊搜索（支持拼写纠错）
    3. 同义词扩展搜索
    4. 拼音搜索
    5. 多字段组合搜索
    6. 自动完成建议
    
    搜索策略（按优先级）：
    1. 单词精确匹配 (boost: 10)
    2. 单词前缀匹配 (boost: 5)
    3. 同义词匹配 (boost: 4)
    4. 单词模糊匹配 (boost: 3)
    5. 释义中文搜索 (boost: 2)
    6. 拼音搜索 (boost: 1.5)
    """
    
    def __init__(
        self,
        es_client: Optional[ElasticsearchClient] = None,
        redis_client=None,
        db_session=None,
        cache_ttl: int = 300
    ):
        """
        初始化搜索器
        
        Args:
            es_client: Elasticsearch客户端
            redis_client: Redis客户端
            db_session: 数据库会话
            cache_ttl: 缓存过期时间（秒）
        """
        self.es = es_client
        self.redis = redis_client
        self.db = db_session
        self.cache_ttl = cache_ttl
        self.index_name = INDEX_NAMES["vocabulary"]
        self.synonym_index = INDEX_NAMES["synonyms"]
        self.suggestion_index = INDEX_NAMES["suggestions"]
    
    async def search(
        self,
        query: str,
        fuzzy: bool = True,
        expand_synonyms: bool = True,
        language: str = "en",
        filters: Optional[Dict[str, Any]] = None,
        size: int = 20,
        from_offset: int = 0
    ) -> List[VocabularySearchResult]:
        """
        搜索词汇
        
        搜索流程: Redis缓存 → Elasticsearch → PostgreSQL(兜底)
        
        Args:
            query: 搜索关键词
            fuzzy: 是否启用模糊搜索（拼写纠错）
            expand_synonyms: 是否扩展同义词
            language: 词汇语言
            filters: 过滤条件，支持 difficulty_level, part_of_speech, tags
            size: 返回结果数
            from_offset: 分页偏移
            
        Returns:
            词汇搜索结果列表
            
        Example:
            >>> results = await searcher.search("happy", fuzzy=True)
            >>> print(results[0].word)  # "happy"
            >>> print(results[0].synonyms)  # ["joyful", "pleased", ...]
        """
        if not query or not query.strip():
            return []
        
        query = query.strip().lower()
        
        # 1. 检查Redis缓存
        cache_key = f"vocab_search:{query}:{fuzzy}:{expand_synonyms}:{language}:{hash(str(filters))}"
        if self.redis:
            cached = await self._get_cache(cache_key)
            if cached:
                logger.info(f"Cache hit for query: {query}")
                return cached
        
        # 2. 构建ES查询
        es_query = self._build_search_query(
            query=query,
            fuzzy=fuzzy,
            expand_synonyms=expand_synonyms,
            language=language,
            filters=filters
        )
        
        # 3. 执行ES搜索
        results = []
        if self.es and self.es.is_connected:
            try:
                response = await self.es.search(
                    index_name=self.index_name,
                    query=es_query["query"],
                    size=size,
                    from_offset=from_offset,
                    sort=es_query.get("sort")
                )
                results = self._parse_es_results(response)
            except Exception as e:
                logger.error(f"ES search error: {e}")
        
        # 4. ES失败或无结果时，回退到PostgreSQL
        if not results and self.db:
            logger.info(f"Fallback to PostgreSQL for query: {query}")
            results = await self._db_search(query, fuzzy, filters, size)
        
        # 5. 写入缓存
        if self.redis and results:
            await self._set_cache(cache_key, results)
        
        return results
    
    def _build_search_query(
        self,
        query: str,
        fuzzy: bool,
        expand_synonyms: bool,
        language: str,
        filters: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        构建Elasticsearch查询
        
        搜索策略（按优先级）：
        1. 单词精确匹配 (boost: 10)
        2. 单词前缀匹配 (boost: 5)
        3. 同义词匹配 (boost: 4)
        4. 单词模糊匹配 (boost: 3)
        5. 释义中文搜索 (boost: 2)
        6. 拼音搜索 (boost: 1.5)
        
        支持：
        - 多字段匹配（词汇、定义、例句）
        - 模糊匹配（编辑距离容错）
        - 同义词扩展
        - 拼音搜索
        """
        should_clauses = []
        filter_clauses = []
        
        # 1. 单词精确匹配 (boost: 10)
        should_clauses.append({
            "term": {
                "word.keyword": {
                    "value": query,
                    "boost": 10
                }
            }
        })
        
        # 2. 单词前缀匹配 (boost: 5)
        should_clauses.append({
            "prefix": {
                "word.keyword": {
                    "value": query,
                    "boost": 5
                }
            }
        })
        
        # 3. 同义词扩展 (boost: 4)
        if expand_synonyms:
            synonyms = self._get_synonyms_from_local(query)
            if synonyms:
                should_clauses.append({
                    "terms": {
                        "word.keyword": synonyms,
                        "boost": 4
                    }
                })
        
        # 4. 单词模糊匹配 (boost: 3)
        if fuzzy:
            should_clauses.append({
                "match": {
                    "word": {
                        "query": query,
                        "fuzziness": "AUTO",
                        "boost": 3
                    }
                }
            })
        
        # 5. 多字段搜索（释义、例句等）
        should_clauses.append({
            "multi_match": {
                "query": query,
                "fields": [
                    "definition_zh^2",
                    "definition_en^1.5",
                    "example_en",
                    "example_translation_zh"
                ],
                "type": "best_fields"
            }
        })
        
        # 6. 拼音搜索（针对中文查询或拼音输入）
        if self._is_chinese(query) or self._is_pinyin(query):
            should_clauses.append({
                "match": {
                    "word.pinyin": {
                        "query": query,
                        "boost": 1.5
                    }
                }
            })
        
        # 构建bool查询
        bool_query = {
            "bool": {
                "should": should_clauses,
                "filter": filter_clauses,
                "minimum_should_match": 1
            }
        }
        
        # 添加过滤条件
        if filters:
            if "difficulty_level" in filters:
                filter_clauses.append({
                    "term": {"difficulty_level": filters["difficulty_level"]}
                })
            if "difficulty" in filters:
                filter_clauses.append({
                    "term": {"difficulty_level": filters["difficulty"]}
                })
            if "part_of_speech" in filters:
                filter_clauses.append({
                    "term": {"part_of_speech": filters["part_of_speech"]}
                })
            if "tags" in filters:
                filter_clauses.append({
                    "terms": {"tags": filters["tags"] if isinstance(filters["tags"], list) else [filters["tags"]]}
                })
            if "language" in filters:
                filter_clauses.append({
                    "term": {"language": filters["language"]}
                })
        
        # 完整查询
        es_query = {
            "query": {
                "bool": bool_query
            },
            "highlight": {
                "pre_tags": ["<mark>"],
                "post_tags": ["</mark>"],
                "fields": {
                    "word": {},
                    "definition_zh": {},
                    "definition_en": {},
                    "example_en": {}
                }
            },
            "sort": [
                {"_score": {"order": "desc"}},
                {"frequency_rank": {"order": "asc"}}
            ]
        }
        
        return es_query
    
    async def _db_search(
        self,
        query: str,
        fuzzy: bool,
        filters: Optional[Dict[str, Any]],
        size: int
    ) -> List[VocabularySearchResult]:
        """
        PostgreSQL兜底搜索
        
        使用pg_trgm扩展支持模糊搜索
        """
        # 这里应该调用实际的数据库查询
        # 示例SQL:
        # SELECT * FROM vocabulary 
        # WHERE word % query OR word ILIKE '%query%'
        # ORDER BY similarity(word, query) DESC
        # LIMIT size
        logger.info(f"DB search for: {query}")
        return []
    
    def _parse_es_results(self, response: Dict[str, Any]) -> List[VocabularySearchResult]:
        """解析ES搜索结果"""
        results = []
        hits = response.get("hits", {}).get("hits", [])
        
        for hit in hits:
            source = hit.get("_source", {})
            highlight = hit.get("highlight", {})
            
            # 获取定义（支持嵌套结构）
            definitions = source.get("definitions", [])
            definition_zh = None
            definition_en = None
            example_en = None
            example_translation_zh = None
            
            if definitions and len(definitions) > 0:
                first_def = definitions[0]
                if isinstance(first_def, dict):
                    definition_zh = first_def.get("definition") if first_def.get("language") == "zh" else None
                    definition_en = first_def.get("definition") if first_def.get("language") == "en" else None
                    example_en = first_def.get("example_sentence")
                    example_translation_zh = first_def.get("example_translation")
            
            # 如果顶层字段存在则使用顶层字段
            definition_zh = source.get("definition_zh", definition_zh)
            definition_en = source.get("definition_en", definition_en)
            example_en = source.get("example_en", example_en)
            example_translation_zh = source.get("example_translation_zh", example_translation_zh)
            
            result = VocabularySearchResult(
                id=source.get("id", ""),
                word=source.get("word", ""),
                pronunciation=source.get("pronunciation"),
                part_of_speech=source.get("part_of_speech"),
                difficulty_level=source.get("difficulty_level", 1),
                definition_zh=definition_zh,
                definition_en=definition_en,
                example_en=example_en,
                example_translation_zh=example_translation_zh,
                tags=source.get("tags", []),
                synonyms=source.get("synonyms", []),
                score=hit.get("_score", 0.0),
                highlights=highlight
            )
            results.append(result)
        
        return results
    
    async def get_suggestions(self, prefix: str, limit: int = 10) -> List[str]:
        """
        自动完成建议
        
        根据输入前缀返回建议词汇列表
        
        Args:
            prefix: 输入前缀
            limit: 返回建议数
            
        Returns:
            建议词汇列表
            
        Example:
            >>> suggestions = await searcher.get_suggestions("ha", limit=5)
            >>> print(suggestions)  # ["happy", "have", "hard", ...]
        """
        if not self.es or not self.es.is_connected:
            return []
        
        if not prefix or len(prefix) < 1:
            return []
        
        prefix = prefix.lower()
        
        # 检查缓存
        cache_key = f"suggestions:{prefix}:{limit}"
        if self.redis:
            cached = await self._get_raw_cache(cache_key)
            if cached:
                return json.loads(cached)
        
        try:
            # 使用completion suggester
            response = await self.es.client.search(
                index=self.suggestion_index,
                body={
                    "suggest": {
                        "word-suggest": {
                            "prefix": prefix,
                            "completion": {
                                "field": "suggest",
                                "size": limit,
                                "fuzzy": {
                                    "fuzziness": "AUTO",
                                    "min_length": 3
                                }
                            }
                        }
                    }
                }
            )
            
            suggestions = response.get("suggest", {}).get("word-suggest", [{}])[0].get("options", [])
            result = [opt["text"] for opt in suggestions]
            
            # 如果completion suggester没有结果，使用prefix查询
            if not result:
                prefix_response = await self.es.search(
                    index_name=self.index_name,
                    query={
                        "prefix": {
                            "word.keyword": prefix
                        }
                    },
                    size=limit,
                    sort=[{"frequency_rank": {"order": "asc"}}]
                )
                hits = prefix_response.get("hits", {}).get("hits", [])
                result = [hit["_source"].get("word", "") for hit in hits]
            
            # 写入缓存
            if self.redis and result:
                await self._set_raw_cache(cache_key, json.dumps(result), ttl=60)
            
            return result
            
        except Exception as e:
            logger.error(f"Get suggestions error: {e}")
            return []
    
    async def get_synonyms(self, word: str) -> List[str]:
        """
        获取词汇同义词
        
        从同义词索引中查询指定词汇的同义词
        
        Args:
            word: 查询词汇
            
        Returns:
            同义词列表
            
        Example:
            >>> synonyms = await searcher.get_synonyms("happy")
            >>> print(synonyms)  # ["joyful", "pleased", "cheerful", ...]
        """
        if not self.es or not self.es.is_connected:
            return self._get_synonyms_from_local(word)
        
        word = word.lower()
        
        # 检查缓存
        cache_key = f"synonyms:{word}"
        if self.redis:
            cached = await self._get_raw_cache(cache_key)
            if cached:
                return json.loads(cached)
        
        try:
            # 从同义词索引查询
            response = await self.es.search(
                index_name=self.synonym_index,
                query={
                    "term": {"word": word}
                },
                size=1
            )
            
            hits = response.get("hits", {}).get("hits", [])
            if hits:
                synonyms = hits[0]["_source"].get("synonyms", [])
            else:
                # 从词汇索引查询
                vocab_response = await self.es.search(
                    index_name=self.index_name,
                    query={
                        "term": {"word.keyword": word}
                    },
                    size=1
                )
                vocab_hits = vocab_response.get("hits", {}).get("hits", [])
                synonyms = vocab_hits[0]["_source"].get("synonyms", []) if vocab_hits else []
            
            # 写入缓存
            if self.redis and synonyms:
                await self._set_raw_cache(cache_key, json.dumps(synonyms), ttl=300)
            
            return synonyms
            
        except Exception as e:
            logger.error(f"Get synonyms error: {e}")
            return self._get_synonyms_from_local(word)
    
    async def spell_check(self, word: str) -> List[str]:
        """
        拼写检查和纠错
        
        例如: "restarant" → ["restaurant"]
        
        Args:
            word: 待检查词汇
            
        Returns:
            建议的正确拼写列表
        """
        if not self.es or not self.es.is_connected:
            return []
        
        word = word.lower()
        
        try:
            # 使用ES的suggester进行拼写纠错
            response = await self.es.client.search(
                index=self.index_name,
                body={
                    "suggest": {
                        "text": word,
                        "word-suggest": {
                            "term": {
                                "field": "word",
                                "suggest_mode": "always",
                                "min_word_length": 3,
                                "prefix_length": 1
                            }
                        }
                    }
                }
            )
            
            suggestions = response.get("suggest", {}).get("word-suggest", [])
            corrections = []
            for sugg in suggestions:
                for option in sugg.get("options", []):
                    corrections.append(option["text"])
            return corrections
            
        except Exception as e:
            logger.error(f"Spell check error: {e}")
            return []
    
    async def _get_cache(self, key: str) -> Optional[List[VocabularySearchResult]]:
        """从Redis获取缓存（搜索结果）"""
        if not self.redis:
            return None
        try:
            data = await self.redis.get(key)
            if data:
                results_data = json.loads(data)
                return [VocabularySearchResult(**r) for r in results_data]
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        return None
    
    async def _set_cache(self, key: str, value: List[VocabularySearchResult], ttl: Optional[int] = None):
        """设置Redis缓存（搜索结果）"""
        if not self.redis:
            return
        try:
            ttl = ttl or self.cache_ttl
            data = json.dumps([r.to_dict() for r in value])
            await self.redis.setex(key, ttl, data)
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    async def _get_raw_cache(self, key: str) -> Optional[str]:
        """从Redis获取原始缓存"""
        if not self.redis:
            return None
        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.error(f"Raw cache get error: {e}")
        return None
    
    async def _set_raw_cache(self, key: str, value: str, ttl: Optional[int] = None):
        """设置Redis原始缓存"""
        if not self.redis:
            return
        try:
            ttl = ttl or self.cache_ttl
            await self.redis.setex(key, ttl, value)
        except Exception as e:
            logger.error(f"Raw cache set error: {e}")
    
    def _is_chinese(self, text: str) -> bool:
        """检查文本是否包含中文"""
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False
    
    def _is_pinyin(self, text: str) -> bool:
        """检查文本是否可能是拼音"""
        # 简单判断：纯小写字母且长度适中
        if not text:
            return False
        if text.isalpha() and text.islower() and 2 <= len(text) <= 15:
            # 排除常见的英文单词
            common_words = {"the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was", "one", "our", "out", "day", "get", "has", "him", "his", "how", "its", "may", "new", "now", "old", "see", "two", "who", "boy", "did", "she", "use", "her", "way", "many", "oil", "sit", "set", "run", "eat", "far", "sea", "eye", "ago", "off", "too", "any", "say", "man", "try", "ask", "end", "why", "let", "put", "say", "she", "try", "way", "own", "say", "too", "old", "tell", "very", "when", "much", "would", "there", "their", "what", "said", "each", "which", "will", "about", "could", "other", "after", "first", "never", "these", "think", "where", "being", "every", "great", "might", "shall", "still", "those", "while", "this", "that", "with", "have", "from", "they", "know", "want", "been", "good", "much", "some", "time", "very", "when", "come", "here", "just", "like", "long", "make", "many", "over", "such", "take", "than", "them", "well", "were"}
            if text in common_words:
                return False
            return True
        return False
    
    def _get_synonyms_from_local(self, word: str) -> List[str]:
        """
        从本地同义词库获取同义词
        
        作为ES查询失败时的兜底方案
        """
        # 基础同义词映射
        synonym_map = {
            "happy": ["joyful", "pleased", "cheerful", "glad", "delighted"],
            "sad": ["unhappy", "sorrowful", "gloomy", "melancholy"],
            "big": ["large", "huge", "enormous", "giant", "vast"],
            "small": ["little", "tiny", "miniature", "petite"],
            "good": ["great", "excellent", "wonderful", "fantastic", "superb"],
            "bad": ["terrible", "awful", "horrible", "poor"],
            "begin": ["start", "commence", "initiate", "launch"],
            "end": ["finish", "complete", "conclude", "terminate"],
            "important": ["significant", "crucial", "vital", "essential"],
            "beautiful": ["pretty", "lovely", "gorgeous", "stunning"],
            "smart": ["intelligent", "clever", "bright", "brilliant"],
            "fast": ["quick", "rapid", "swift", "speedy"],
            "slow": ["sluggish", "gradual", "unhurried"],
            "strong": ["powerful", "mighty", "sturdy", "robust"],
            "weak": ["feeble", "fragile", "frail", "delicate"],
            "rich": ["wealthy", "affluent", "prosperous"],
            "poor": ["impoverished", "needy", "destitute"],
            "love": ["adore", "cherish", "worship", "idolize"],
            "hate": ["despise", "loathe", "detest", "abhor"],
            "help": ["assist", "aid", "support", "lend a hand"],
            "make": ["create", "produce", "manufacture", "construct"],
            "get": ["obtain", "acquire", "receive", "gain"],
            "use": ["utilize", "employ", "apply", "operate"],
            "say": ["speak", "state", "declare", "announce"],
            "go": ["move", "proceed", "travel", "advance"],
            "come": ["arrive", "approach", "reach", "enter"],
            "see": ["look", "view", "observe", "watch"],
            "know": ["understand", "comprehend", "realize", "recognize"],
            "think": ["believe", "consider", "suppose", "assume"],
            "want": ["desire", "wish", "crave", "long for"],
            "need": ["require", "demand", "necessitate"],
            "like": ["enjoy", "appreciate", "fancy", "prefer"],
            "find": ["discover", "locate", "detect", "uncover"],
            "tell": ["inform", "notify", "advise", "reveal"],
            "ask": ["inquire", "question", "query", "request"],
            "work": ["labor", "toil", "function", "operate"],
            "seem": ["appear", "look", "sound"],
            "feel": ["sense", "perceive", "experience"],
            "try": ["attempt", "endeavor", "strive", "struggle"],
            "leave": ["depart", "exit", "abandon", "forsake"],
            "call": ["phone", "telephone", "ring", "summon"],
            "goodbye": ["farewell", "bye", "see you", "take care"],
            "hello": ["hi", "hey", "greetings", "welcome"],
            "thanks": ["thank you", "gratitude", "appreciation"],
            "sorry": ["apologize", "regret", "pardon", "excuse"],
            "please": ["kindly", "if you please"],
            "yes": ["yeah", "yep", "sure", "absolutely"],
            "no": ["nope", "nah", "never", "not at all"],
            "restaurant": ["eatery", "diner", "cafe", "bistro"]
        }
        return synonym_map.get(word.lower(), [])


# 便捷函数
async def search_vocabulary(
    query: str,
    fuzzy: bool = True,
    expand_synonyms: bool = True,
    **kwargs
) -> List[VocabularySearchResult]:
    """
    搜索词汇的便捷函数
    
    Args:
        query: 搜索关键词
        fuzzy: 是否启用模糊搜索（拼写纠错）
        expand_synonyms: 是否扩展同义词
        **kwargs: 其他参数
        
    Returns:
        搜索结果列表
        
    Example:
        >>> results = await search_vocabulary("happy", fuzzy=True)
        >>> print(results[0].word)  # "happy"
        >>> print(results[0].synonyms)  # ["joyful", "pleased", ...]
    """
    searcher = VocabularySearcher()
    return await searcher.search(query, fuzzy=fuzzy, expand_synonyms=expand_synonyms, **kwargs)


async def get_suggestions(prefix: str, limit: int = 10) -> List[str]:
    """
    获取搜索建议的便捷函数
    
    Args:
        prefix: 输入前缀
        limit: 返回建议数
        
    Returns:
        建议词汇列表
    """
    searcher = VocabularySearcher()
    return await searcher.get_suggestions(prefix, limit)


async def get_synonyms(word: str) -> List[str]:
    """
    获取同义词的便捷函数
    
    Args:
        word: 查询词汇
        
    Returns:
        同义词列表
    """
    searcher = VocabularySearcher()
    return await searcher.get_synonyms(word)
