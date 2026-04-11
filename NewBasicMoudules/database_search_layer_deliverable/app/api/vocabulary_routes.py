# =====================================================
# AI外语学习系统 - 词汇API路由
# 版本: 1.0.0
# 描述: 提供词汇相关的RESTful API
# =====================================================

from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import get_async_session
from ..services.vocabulary_service import VocabularyService

router = APIRouter(prefix="/vocabulary", tags=["vocabulary"])


# -----------------------------------------------------
# Pydantic模型
# -----------------------------------------------------

class DefinitionCreate(BaseModel):
    """定义创建模型"""
    definition: str = Field(..., description="定义内容")
    language: str = Field(default="zh", description="定义语言")
    example_sentence: Optional[str] = Field(None, description="例句")
    example_translation: Optional[str] = Field(None, description="例句翻译")
    source: Optional[str] = Field(None, description="来源")


class DefinitionResponse(DefinitionCreate):
    """定义响应模型"""
    id: str
    
    class Config:
        from_attributes = True


class VocabularyCreate(BaseModel):
    """词汇创建模型"""
    word: str = Field(..., min_length=1, max_length=255, description="单词")
    language: str = Field(default="en", description="语言代码")
    pronunciation: Optional[str] = Field(None, description="音标")
    part_of_speech: Optional[str] = Field(None, description="词性")
    difficulty_level: int = Field(default=1, ge=1, le=5, description="难度等级")
    frequency_rank: Optional[int] = Field(None, description="频率排名")
    definitions: List[DefinitionCreate] = Field(default=[], description="定义列表")
    tags: List[str] = Field(default=[], description="标签列表")


class VocabularyResponse(BaseModel):
    """词汇响应模型"""
    id: str
    word: str
    language: str
    pronunciation: Optional[str]
    part_of_speech: Optional[str]
    difficulty_level: int
    frequency_rank: Optional[int]
    definitions: List[DefinitionResponse]
    tags: List[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    
    class Config:
        from_attributes = True


class SynonymResponse(BaseModel):
    """同义词响应模型"""
    id: str
    word: str
    pronunciation: Optional[str]
    part_of_speech: Optional[str]
    relation_strength: float


class BulkImportRequest(BaseModel):
    """批量导入请求模型"""
    vocabulary: List[VocabularyCreate]


class BulkImportResponse(BaseModel):
    """批量导入响应模型"""
    success: int
    failed: int
    errors: List[dict]


# -----------------------------------------------------
# 依赖注入
# -----------------------------------------------------

async def get_vocab_service(
    db: AsyncSession = Depends(get_async_session)
) -> VocabularyService:
    """获取词汇服务实例"""
    return VocabularyService(db)


# -----------------------------------------------------
# API路由
# -----------------------------------------------------

@router.get(
    "/{vocab_id}",
    response_model=VocabularyResponse,
    summary="获取词汇详情",
    description="根据词汇ID获取详细信息"
)
async def get_vocabulary(
    vocab_id: UUID,
    service: VocabularyService = Depends(get_vocab_service)
):
    """
    获取词汇详情
    
    - **vocab_id**: 词汇UUID
    """
    vocab = await service.get_vocabulary_by_id(vocab_id)
    if not vocab:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vocabulary with ID {vocab_id} not found"
        )
    return vocab


@router.get(
    "/word/{word}",
    response_model=VocabularyResponse,
    summary="根据单词获取词汇",
    description="根据单词文本获取词汇详情"
)
async def get_vocabulary_by_word(
    word: str,
    language: str = Query(default="en", description="语言代码"),
    service: VocabularyService = Depends(get_vocab_service)
):
    """
    根据单词获取词汇详情
    
    - **word**: 单词文本
    - **language**: 语言代码（默认: en）
    """
    vocab = await service.get_vocabulary_by_word(word, language)
    if not vocab:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vocabulary '{word}' not found"
        )
    return vocab


@router.get(
    "/",
    response_model=List[VocabularyResponse],
    summary="搜索词汇",
    description="使用PostgreSQL进行模糊搜索"
)
async def search_vocabulary(
    query: str = Query(..., description="搜索词"),
    language: str = Query(default="en", description="语言代码"),
    limit: int = Query(default=20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    service: VocabularyService = Depends(get_vocab_service)
):
    """
    搜索词汇（PostgreSQL模糊搜索）
    
    - **query**: 搜索词
    - **language**: 语言代码
    - **limit**: 返回数量限制
    - **offset**: 偏移量
    """
    results = await service.search_vocabulary(
        query=query,
        language=language,
        limit=limit,
        offset=offset
    )
    return results


@router.get(
    "/{vocab_id}/synonyms",
    response_model=List[SynonymResponse],
    summary="获取同义词",
    description="获取词汇的同义词列表"
)
async def get_synonyms(
    vocab_id: UUID,
    min_strength: float = Query(default=0.5, ge=0, le=1, description="最小关联强度"),
    service: VocabularyService = Depends(get_vocab_service)
):
    """
    获取词汇的同义词
    
    - **vocab_id**: 词汇UUID
    - **min_strength**: 最小关联强度（0-1）
    """
    synonyms = await service.get_synonyms(vocab_id, min_strength)
    return synonyms


@router.post(
    "/{vocab_id}/synonyms/{target_vocab_id}",
    status_code=status.HTTP_201_CREATED,
    summary="添加同义词关系",
    description="在两个词汇之间建立同义词关系"
)
async def add_synonym_relation(
    vocab_id: UUID,
    target_vocab_id: UUID,
    relation_strength: float = Query(default=1.0, ge=0, le=1),
    service: VocabularyService = Depends(get_vocab_service)
):
    """
    添加同义词关系
    
    - **vocab_id**: 源词汇ID
    - **target_vocab_id**: 目标词汇ID
    - **relation_strength**: 关联强度（0-1）
    """
    success = await service.add_synonym_relation(
        vocab_id, target_vocab_id, relation_strength
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to add synonym relation"
        )
    return {"message": "Synonym relation added successfully"}


@router.get(
    "/tags/search",
    response_model=List[VocabularyResponse],
    summary="根据标签搜索词汇",
    description="根据标签名称搜索词汇"
)
async def get_vocabulary_by_tags(
    tags: List[str] = Query(..., description="标签名称列表"),
    language: str = Query(default="en", description="语言代码"),
    limit: int = Query(default=20, ge=1, le=100),
    service: VocabularyService = Depends(get_vocab_service)
):
    """
    根据标签搜索词汇
    
    - **tags**: 标签名称列表
    - **language**: 语言代码
    - **limit**: 返回数量限制
    """
    results = await service.get_vocabulary_by_tags(tags, language, limit)
    return results


@router.post(
    "/bulk-import",
    response_model=BulkImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="批量导入词汇",
    description="批量导入词汇数据"
)
async def bulk_import_vocabulary(
    request: BulkImportRequest,
    service: VocabularyService = Depends(get_vocab_service)
):
    """
    批量导入词汇
    
    请求体示例：
    ```json
    {
        "vocabulary": [
            {
                "word": "example",
                "language": "en",
                "pronunciation": "/ɪɡˈzæmpl/",
                "part_of_speech": "noun",
                "difficulty_level": 2,
                "definitions": [
                    {
                        "definition": "例子，实例",
                        "language": "zh",
                        "example_sentence": "This is an example.",
                        "example_translation": "这是一个例子。"
                    }
                ],
                "tags": ["beginner", "daily"]
            }
        ]
    }
    ```
    """
    # 转换Pydantic模型为字典
    vocab_data = [v.model_dump() for v in request.vocabulary]
    result = await service.bulk_import_vocabulary(vocab_data)
    return BulkImportResponse(**result)
