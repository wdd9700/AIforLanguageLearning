# =====================================================
# AI外语学习系统 - 搜索API路由
# 版本: 1.0.0
# 描述: 提供全文搜索、模糊搜索、同义词扩展等API
# =====================================================

from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


# -----------------------------------------------------
# Pydantic模型
# -----------------------------------------------------

class SearchRequest(BaseModel):
    """搜索请求模型"""
    query: str = Field(..., min_length=1, description="搜索词")
    fuzzy: bool = Field(default=True, description="是否启用模糊搜索")
    expand_synonyms: bool = Field(default=True, description="是否扩展同义词")
    language: str = Field(default="en", description="语言代码")
    size: int = Field(default=20, ge=1, le=100, description="返回结果数量")


class SearchResultItem(BaseModel):
    """搜索结果项模型"""
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


class SearchResponse(BaseModel):
    """搜索响应模型"""
    query: str
    results: List[SearchResultItem]
    total: int
    source: Optional[str] = Field(None, description="数据来源: cache, elasticsearch, postgresql")
    time_ms: int = Field(..., description="搜索耗时（毫秒）")


class SuggestionResponse(BaseModel):
    """搜索建议响应模型"""
    query: str
    suggestions: List[str]


class SynonymSearchResponse(BaseModel):
    """同义词搜索响应模型"""
    query: str
    expanded_terms: List[str]
    results: List[SearchResultItem]
    total: int
    time_ms: int


class FuzzySearchResponse(BaseModel):
    """模糊搜索响应模型"""
    query: str
    corrected_query: Optional[str] = Field(None, description="纠正后的查询词")
    results: List[SearchResultItem]
    total: int
    time_ms: int


class SynonymListResponse(BaseModel):
    """同义词列表响应模型"""
    word: str
    synonyms: List[Dict[str, Any]]


# -----------------------------------------------------
# 依赖注入
# -----------------------------------------------------

# 注意：实际使用时需要配置好SearchService的依赖注入
# 这里使用一个占位函数，实际项目中应该使用依赖注入容器
async def get_search_service() -> SearchService:
    """获取搜索服务实例"""
    # 实际项目中这里应该注入配置好的SearchService
    raise NotImplementedError("SearchService dependency not configured")


# -----------------------------------------------------
# API路由
# -----------------------------------------------------

@router.post(
    "/vocabulary",
    response_model=SearchResponse,
    summary="搜索词汇",
    description="多层搜索：Redis缓存 → Elasticsearch → PostgreSQL"
)
async def search_vocabulary(
    request: SearchRequest,
    # service: SearchService = Depends(get_search_service)  # 取消注释以使用依赖注入
):
    """
    搜索词汇
    
    搜索流程：
    1. 首先检查Redis缓存
    2. 缓存未命中则查询Elasticsearch
    3. ES无结果则使用PostgreSQL兜底
    
    支持功能：
    - 精确匹配
    - 模糊搜索（拼写纠错）
    - 同义词扩展
    - 拼音搜索
    
    请求示例：
    ```json
    {
        "query": "happy",
        "fuzzy": true,
        "expand_synonyms": true,
        "language": "en",
        "size": 20
    }
    ```
    """
    # 这里应该调用service.search_vocabulary
    # 由于依赖注入未配置，返回示例响应
    return SearchResponse(
        query=request.query,
        results=[],
        total=0,
        source="not_implemented",
        time_ms=0
    )


@router.get(
    "/vocabulary",
    response_model=SearchResponse,
    summary="搜索词汇（GET方式）",
    description="使用查询参数进行词汇搜索"
)
async def search_vocabulary_get(
    query: str = Query(..., min_length=1, description="搜索词"),
    fuzzy: bool = Query(default=True, description="是否启用模糊搜索"),
    expand_synonyms: bool = Query(default=True, description="是否扩展同义词"),
    language: str = Query(default="en", description="语言代码"),
    size: int = Query(default=20, ge=1, le=100, description="返回结果数量"),
    use_cache: bool = Query(default=True, description="是否使用缓存"),
    # service: SearchService = Depends(get_search_service)
):
    """
    搜索词汇（GET方式）
    
    - **query**: 搜索词
    - **fuzzy**: 是否启用模糊搜索（默认: true）
    - **expand_synonyms**: 是否扩展同义词（默认: true）
    - **language**: 语言代码（默认: en）
    - **size**: 返回结果数量（默认: 20）
    - **use_cache**: 是否使用缓存（默认: true）
    """
    # 这里应该调用service.search_vocabulary
    return SearchResponse(
        query=query,
        results=[],
        total=0,
        source="not_implemented",
        time_ms=0
    )


@router.get(
    "/suggestions",
    response_model=SuggestionResponse,
    summary="获取搜索建议",
    description="根据部分输入获取自动完成建议"
)
async def get_search_suggestions(
    query: str = Query(..., min_length=1, description="部分输入"),
    language: str = Query(default="en", description="语言代码"),
    size: int = Query(default=10, ge=1, le=20, description="建议数量"),
    # service: SearchService = Depends(get_search_service)
):
    """
    获取搜索建议（自动完成）
    
    - **query**: 部分输入文本
    - **language**: 语言代码
    - **size**: 建议数量
    
    示例：
    - 输入 "ha" 可能返回 ["happy", "have", "hard", "hand"]
    """
    # 这里应该调用service.get_search_suggestions
    return SuggestionResponse(
        query=query,
        suggestions=[]
    )


@router.get(
    "/synonyms",
    response_model=SynonymSearchResponse,
    summary="同义词扩展搜索",
    description="搜索词汇及其同义词"
)
async def search_with_synonyms(
    query: str = Query(..., min_length=1, description="搜索词"),
    language: str = Query(default="en", description="语言代码"),
    size: int = Query(default=20, ge=1, le=100, description="返回结果数量"),
    # service: SearchService = Depends(get_search_service)
):
    """
    同义词扩展搜索
    
    示例：搜索 "happy" 会同时返回 "joyful, pleased, cheerful" 等相关词汇
    
    - **query**: 搜索词
    - **language**: 语言代码
    - **size**: 返回结果数量
    """
    # 这里应该调用service.search_with_synonyms
    return SynonymSearchResponse(
        query=query,
        expanded_terms=[],
        results=[],
        total=0,
        time_ms=0
    )


@router.get(
    "/fuzzy",
    response_model=FuzzySearchResponse,
    summary="模糊搜索",
    description="支持拼写纠错的模糊搜索"
)
async def fuzzy_search(
    query: str = Query(..., min_length=1, description="搜索词（可能有拼写错误）"),
    language: str = Query(default="en", description="语言代码"),
    size: int = Query(default=20, ge=1, le=100, description="返回结果数量"),
    # service: SearchService = Depends(get_search_service)
):
    """
    模糊搜索（拼写纠错）
    
    示例：
    - 搜索 "restarant" 能匹配到 "restaurant"
    - 搜索 "accomodate" 能匹配到 "accommodate"
    
    - **query**: 搜索词
    - **language**: 语言代码
    - **size**: 返回结果数量
    """
    # 这里应该调用service.fuzzy_search
    return FuzzySearchResponse(
        query=query,
        corrected_query=None,
        results=[],
        total=0,
        time_ms=0
    )


@router.get(
    "/word/{word}/synonyms",
    response_model=SynonymListResponse,
    summary="获取单词的同义词",
    description="获取指定单词的同义词列表"
)
async def get_synonyms_for_word(
    word: str,
    language: str = Query(default="en", description="语言代码"),
    # service: SearchService = Depends(get_search_service)
):
    """
    获取单词的同义词
    
    示例：
    - "happy" → ["joyful", "pleased", "cheerful", "delighted"]
    
    - **word**: 单词
    - **language**: 语言代码
    """
    # 这里应该调用service.get_synonyms_for_word
    return SynonymListResponse(
        word=word,
        synonyms=[]
    )


@router.post(
    "/cache/invalidate",
    status_code=status.HTTP_200_OK,
    summary="使搜索缓存失效",
    description="清除搜索缓存"
)
async def invalidate_search_cache(
    query_pattern: Optional[str] = Query(default=None, description="查询模式，为空则清除所有"),
    # service: SearchService = Depends(get_search_service)
):
    """
    使搜索缓存失效
    
    - **query_pattern**: 查询模式，如果为None则清除所有搜索缓存
    
    返回清除的缓存条目数量
    """
    # 这里应该调用service.invalidate_search_cache
    return {
        "message": "Cache invalidation not implemented",
        "invalidated_count": 0
    }
