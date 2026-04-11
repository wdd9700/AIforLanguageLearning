from __future__ import annotations

from typing import Literal, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..db import get_session
from ..llm import generate_definition, generate_vocab_fields
from ..models import PublicVocabEntry, UserVocabQuery
from ..ocr import ocr_image_base64
from ..knowledge_graph.service import get_kg_service, KnowledgeGraphService
from ..knowledge_graph.models import RelationType, RecommendationResult

router = APIRouter(prefix="/v1/vocab", tags=["vocab"])


class VocabLookupRequest(BaseModel):
    term: str
    source: Literal["manual", "ocr"] = "manual"
    session_id: str = ""
    conversation_id: str = ""


class VocabLookupResponse(BaseModel):
    term: str
    definition: str
    from_public_vocab: bool


class VocabLookupOcrRequest(BaseModel):
    image: str
    language: str = "english"
    session_id: str = ""
    conversation_id: str = ""


class VocabLookupOcrResponse(BaseModel):
    term: str
    ocr_text: str
    meaning: str
    example: str
    example_translation: str


@router.post("/lookup", response_model=VocabLookupResponse)
async def lookup_vocab(
    req: VocabLookupRequest,
    session: Session = Depends(get_session),
) -> VocabLookupResponse:
    """
    查词API
    
    关键约束: 查词未命中时，LLM生成词汇后必须写入知识图谱建立关系
    """
    term = (req.term or "").strip()
    if not term:
        raise HTTPException(status_code=400, detail="term is required")

    entry = session.exec(select(PublicVocabEntry).where(PublicVocabEntry.term == term)).first()

    if entry is not None and entry.definition:
        definition = entry.definition
        from_public_vocab = True
    else:
        # LLM生成词汇
        definition = await generate_definition(term)
        from_public_vocab = False
        
        # ⚠️ 关键约束: LLM生成后必须写入知识图谱建立关系
        try:
            kg_service = await get_kg_service()
            
            # 1. 添加词汇节点
            await kg_service.add_word(
                word=term,
                meaning=definition[:200] if len(definition) > 200 else definition,
            )
            
            # 2. 自动构建同根词关系
            cognates = await kg_service.auto_build_cognate_relations(term)
            if cognates:
                print(f"✅ Auto-built cognate relations for '{term}': {cognates}")
            
        except Exception as e:
            # 不影响主流程，仅记录日志
            print(f"⚠️ Failed to build knowledge graph for '{term}': {e}")

    session.add(
        UserVocabQuery(
            session_id=req.session_id,
            conversation_id=req.conversation_id,
            term=term,
            source=req.source,
            result=definition,
        )
    )
    session.commit()

    return VocabLookupResponse(term=term, definition=definition, from_public_vocab=from_public_vocab)


@router.post("/lookup-ocr", response_model=VocabLookupOcrResponse)
async def lookup_vocab_ocr(
    req: VocabLookupOcrRequest,
    session: Session = Depends(get_session),
) -> VocabLookupOcrResponse:
    ocr_text = ocr_image_base64(req.image, language=req.language)
    if not ocr_text:
        raise HTTPException(status_code=400, detail="OCR failed or empty text")

    term = ocr_text.splitlines()[0].strip() if ocr_text.splitlines() else ocr_text.strip()
    if not term:
        raise HTTPException(status_code=400, detail="OCR text is empty")

    fields = await generate_vocab_fields(term)
    meaning = str(fields.get("meaning") or "").strip()
    example = str(fields.get("example") or "").strip()
    example_translation = str(fields.get("example_translation") or "").strip()

    if not meaning:
        definition = await generate_definition(term)
        if "\n" in definition:
            lines = [ln.strip() for ln in definition.splitlines() if ln.strip()]
            if lines:
                meaning = lines[0].removeprefix("释义：").strip() or meaning
            if len(lines) > 1:
                example = lines[1].removeprefix("例句：").strip() or example

    session.add(
        UserVocabQuery(
            session_id=req.session_id,
            conversation_id=req.conversation_id,
            term=term,
            source="ocr",
            result=meaning or example or "",
        )
    )
    session.commit()

    return VocabLookupOcrResponse(
        term=term,
        ocr_text=ocr_text,
        meaning=meaning or "暂无",
        example=example,
        example_translation=example_translation,
    )


# ==================== 知识图谱相关API ====================


class WordRelationsRequest(BaseModel):
    """词汇关系查询请求"""
    word: str = Field(..., description="查询的词汇")
    relation_type: Literal["synonym", "antonym", "cognate", "similar_form", "all"] = Field(
        default="all", description="关系类型"
    )
    limit: int = Field(default=10, ge=1, le=50, description="返回数量限制")


class WordRelationItem(BaseModel):
    """单个词汇关系项"""
    word: str
    relation_type: str
    strength: float
    meaning: str | None = None


class WordRelationsResponse(BaseModel):
    """词汇关系查询响应"""
    word: str
    relations: List[WordRelationItem]
    total: int


@router.post("/relations", response_model=WordRelationsResponse)
async def get_word_relations(req: WordRelationsRequest) -> WordRelationsResponse:
    """
    获取词汇关系
    
    核心功能 - 验收标准:
    - "unhappy" 能召回 "happy" (反义词)
    - "unhappy" 能召回 "unfortunate" (近义词)
    
    使用示例:
    ```json
    {
        "word": "unhappy",
        "relation_type": "antonym",
        "limit": 5
    }
    ```
    """
    word = (req.word or "").strip().lower()
    if not word:
        raise HTTPException(status_code=400, detail="word is required")
    
    kg_service = await get_kg_service()
    
    # 转换关系类型参数
    relation_type = None if req.relation_type == "all" else req.relation_type
    
    # 查询关系
    result = await kg_service.get_word_relations(
        word=word,
        relation_type=relation_type,
        limit=req.limit,
    )
    
    # 转换为响应格式
    relations = [
        WordRelationItem(
            word=r.target,
            relation_type=r.relation_type.value,
            strength=r.strength,
            meaning=None,  # 可以从Neo4j获取
        )
        for r in result.relations
    ]
    
    return WordRelationsResponse(
        word=word,
        relations=relations,
        total=result.total,
    )


@router.get("/relations/{word}", response_model=WordRelationsResponse)
async def get_word_relations_get(
    word: str,
    relation_type: Literal["synonym", "antonym", "cognate", "similar_form", "all"] = "all",
    limit: int = 10,
) -> WordRelationsResponse:
    """GET方式获取词汇关系"""
    return await get_word_relations(
        WordRelationsRequest(
            word=word,
            relation_type=relation_type,
            limit=limit,
        )
    )


class VocabRecommendRequest(BaseModel):
    """词汇推荐请求"""
    user_id: str = Field(..., description="用户ID")
    count: int = Field(default=10, ge=1, le=20, description="推荐数量")
    user_level: int = Field(default=1, ge=1, le=6, description="用户等级 1-6")
    weak_points: List[str] = Field(default_factory=list, description="薄弱词汇点")
    learned_words: List[str] = Field(default_factory=list, description="已学词汇")


class VocabRecommendItem(BaseModel):
    """推荐词汇项"""
    word: str
    reason: str
    score: float
    relation_type: str | None = None


class VocabRecommendResponse(BaseModel):
    """词汇推荐响应"""
    user_id: str
    recommendations: List[VocabRecommendItem]
    total: int


@router.post("/recommend", response_model=VocabRecommendResponse)
async def recommend_vocabulary(req: VocabRecommendRequest) -> VocabRecommendResponse:
    """
    词汇推荐
    
    算法逻辑:
    - 薄弱点匹配 (30%): 推荐与薄弱点相关的词汇
    - 协同过滤 (40%): 基于相似用户的学习记录
    - 内容相似 (30%): 基于词汇关系图谱
    
    验收标准: 推荐准确率 > 30%
    
    使用示例:
    ```json
    {
        "user_id": "user_001",
        "count": 5,
        "user_level": 2,
        "weak_points": ["happy", "sad"],
        "learned_words": ["good", "bad"]
    }
    ```
    """
    if not req.user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    kg_service = await get_kg_service()
    
    result = await kg_service.recommend_vocabulary(
        user_id=req.user_id,
        n=req.count,
        user_level=req.user_level,
        weak_points=req.weak_points,
        learned_words=req.learned_words,
    )
    
    recommendations = [
        VocabRecommendItem(
            word=r.word,
            reason=r.reason,
            score=r.score,
            relation_type=r.relation_type.value if r.relation_type else None,
        )
        for r in result.recommendations
    ]
    
    return VocabRecommendResponse(
        user_id=req.user_id,
        recommendations=recommendations,
        total=result.total,
    )


# ==================== 管理API ====================


class AddRelationRequest(BaseModel):
    """添加词汇关系请求"""
    source: str = Field(..., description="源词汇")
    target: str = Field(..., description="目标词汇")
    relation_type: Literal["synonym", "antonym", "cognate", "similar_form"] = Field(
        ..., description="关系类型"
    )
    strength: float = Field(default=1.0, ge=0.0, le=1.0, description="关系强度")


class AddRelationResponse(BaseModel):
    """添加词汇关系响应"""
    success: bool
    message: str


@router.post("/relations/add", response_model=AddRelationResponse)
async def add_word_relation(req: AddRelationRequest) -> AddRelationResponse:
    """
    添加词汇关系（管理接口）
    
    使用场景:
    - LLM生成词汇后自动建立关系
    - 批量导入词库数据
    - 用户反馈纠正关系
    """
    kg_service = await get_kg_service()
    
    relation_type = RelationType(req.relation_type)
    
    success = await kg_service.add_word_relation(
        source=req.source,
        target=req.target,
        relation_type=relation_type,
        strength=req.strength,
    )
    
    return AddRelationResponse(
        success=success,
        message="Relation added successfully" if success else "Failed to add relation",
    )


# ==================== 知识图谱增强API ====================


class CognateAnalysisRequest(BaseModel):
    """同根词分析请求"""
    word: str = Field(..., description="要分析的词汇")


class CognateItem(BaseModel):
    """同根词项"""
    word: str
    type: str  # prefix 或 suffix
    affix: str
    meaning: str


class CognateAnalysisResponse(BaseModel):
    """同根词分析响应"""
    word: str
    cognates: List[CognateItem]
    total: int


@router.post("/cognates/analyze", response_model=CognateAnalysisResponse)
async def analyze_cognates(req: CognateAnalysisRequest) -> CognateAnalysisResponse:
    """
    分析词汇的同根词（基于词根词缀规则）
    
    示例:
    - "unhappy" -> [{"word": "happy", "type": "prefix", "affix": "un", "meaning": "否定"}]
    - "happiness" -> [{"word": "happy", "type": "suffix", "affix": "ness", "meaning": "名词(性质)"}]
    """
    word = (req.word or "").strip()
    if not word:
        raise HTTPException(status_code=400, detail="word is required")
    
    kg_service = await get_kg_service()
    cognates = kg_service.analyze_cognates(word)
    
    return CognateAnalysisResponse(
        word=word,
        cognates=[CognateItem(**c) for c in cognates],
        total=len(cognates),
    )


class LearningPathRequest(BaseModel):
    """学习路径请求"""
    start_word: str = Field(..., description="起始词汇")
    target_word: str = Field(..., description="目标词汇")
    max_depth: int = Field(default=5, ge=1, le=10, description="最大搜索深度")


class LearningPathStep(BaseModel):
    """学习路径步骤"""
    from_word: str
    to_word: str
    relation: str
    strength: float


class LearningPathResponse(BaseModel):
    """学习路径响应"""
    start_word: str
    target_word: str
    path: List[LearningPathStep]
    total_steps: int
    found: bool


@router.post("/learning-path", response_model=LearningPathResponse)
async def generate_learning_path(req: LearningPathRequest) -> LearningPathResponse:
    """
    生成词汇学习路径（A*算法）
    
    从start_word到target_word的最短学习路径
    基于词汇关系图谱的图搜索
    """
    start = (req.start_word or "").strip()
    target = (req.target_word or "").strip()
    
    if not start or not target:
        raise HTTPException(status_code=400, detail="start_word and target_word are required")
    
    kg_service = await get_kg_service()
    path = await kg_service.generate_learning_path(
        start_word=start,
        target_word=target,
        max_depth=req.max_depth,
    )
    
    return LearningPathResponse(
        start_word=start,
        target_word=target,
        path=[LearningPathStep(**step) for step in path],
        total_steps=len(path),
        found=len(path) > 0,
    )


class LightFMTrainRequest(BaseModel):
    """LightFM训练请求"""
    interactions: List[dict] = Field(..., description="用户-物品交互数据")
    user_features: Optional[Dict[str, List[str]]] = None
    item_features: Optional[Dict[str, List[str]]] = None


class LightFMTrainResponse(BaseModel):
    """LightFM训练响应"""
    success: bool
    message: str


@router.post("/recommend/train", response_model=LightFMTrainResponse)
async def train_lightfm_model(req: LightFMTrainRequest) -> LightFMTrainResponse:
    """
    训练LightFM协同过滤模型
    
    输入用户-物品交互数据，训练推荐模型
    """
    kg_service = await get_kg_service()
    
    # 转换交互数据格式
    interactions = [
        (item["user_id"], item["word"], item.get("weight", 1.0))
        for item in req.interactions
    ]
    
    success = await kg_service.train_lightfm_model(
        user_item_interactions=interactions,
        user_features=req.user_features,
        item_features=req.item_features,
    )
    
    return LightFMTrainResponse(
        success=success,
        message="Model trained successfully" if success else "Training failed or LightFM not available",
    )


class FAISSBuildRequest(BaseModel):
    """FAISS索引构建请求"""
    embeddings: Dict[str, List[float]] = Field(..., description="词汇向量映射 {word: [vector]}")
    embedding_dim: int = Field(default=100, description="向量维度")


class FAISSBuildResponse(BaseModel):
    """FAISS索引构建响应"""
    success: bool
    message: str
    word_count: int


@router.post("/search/build-index", response_model=FAISSBuildResponse)
async def build_faiss_index(req: FAISSBuildRequest) -> FAISSBuildResponse:
    """
    构建FAISS向量索引
    
    用于语义相似度搜索
    """
    kg_service = await get_kg_service()
    
    success = await kg_service.build_faiss_index(
        word_embeddings=req.embeddings,
        embedding_dim=req.embedding_dim,
    )
    
    return FAISSBuildResponse(
        success=success,
        message="Index built successfully" if success else "Index building failed or FAISS not available",
        word_count=len(req.embeddings),
    )


class FAISSSearchRequest(BaseModel):
    """FAISS搜索请求"""
    query_word: str = Field(..., description="查询词汇")
    n: int = Field(default=10, ge=1, le=50, description="返回数量")


class FAISSSearchItem(BaseModel):
    """FAISS搜索结果项"""
    word: str
    reason: str
    score: float


class FAISSSearchResponse(BaseModel):
    """FAISS搜索响应"""
    query_word: str
    results: List[FAISSSearchItem]
    total: int


@router.post("/search/similar", response_model=FAISSSearchResponse)
async def search_similar_words(req: FAISSSearchRequest) -> FAISSSearchResponse:
    """
    使用FAISS搜索相似词汇
    
    基于语义向量相似度
    """
    word = (req.query_word or "").strip()
    if not word:
        raise HTTPException(status_code=400, detail="query_word is required")
    
    kg_service = await get_kg_service()
    results = await kg_service.search_similar_words(
        query_word=word,
        n=req.n,
    )
    
    return FAISSSearchResponse(
        query_word=word,
        results=[FAISSSearchItem(word=r.word, reason=r.reason, score=r.score) for r in results],
        total=len(results),
    )
