# =====================================================
# AI外语学习系统 - 词汇服务层
# 版本: 1.0.0
# 描述: 提供词汇的CRUD操作和业务逻辑
# =====================================================

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import (
    Vocabulary, VocabularyDefinition, Tag, 
    vocabulary_tags, SynonymRelation
)

logger = logging.getLogger(__name__)


class VocabularyService:
    """
    词汇服务层
    
    功能：
    1. 词汇CRUD操作
    2. 同义词管理
    3. 标签管理
    4. 批量导入导出
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        初始化服务
        
        Args:
            db_session: 异步数据库会话
        """
        self.db = db_session
    
    async def get_vocabulary_by_id(
        self, 
        vocab_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        根据ID获取词汇详情
        
        Args:
            vocab_id: 词汇ID
            
        Returns:
            词汇详情字典或None
        """
        result = await self.db.execute(
            select(Vocabulary).where(Vocabulary.id == vocab_id)
        )
        vocab = result.scalar_one_or_none()
        
        if not vocab:
            return None
            
        return await self._vocab_to_dict(vocab)
    
    async def get_vocabulary_by_word(
        self, 
        word: str, 
        language: str = "en"
    ) -> Optional[Dict[str, Any]]:
        """
        根据单词获取词汇详情
        
        Args:
            word: 单词
            language: 语言代码
            
        Returns:
            词汇详情字典或None
        """
        result = await self.db.execute(
            select(Vocabulary).where(
                and_(
                    Vocabulary.word == word,
                    Vocabulary.language == language
                )
            )
        )
        vocab = result.scalar_one_or_none()
        
        if not vocab:
            return None
            
        return await self._vocab_to_dict(vocab)
    
    async def search_vocabulary(
        self,
        query: str,
        language: str = "en",
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        使用PostgreSQL模糊搜索词汇
        
        Args:
            query: 搜索词
            language: 语言代码
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            词汇列表
        """
        # 使用pg_trgm进行模糊匹配
        result = await self.db.execute(
            select(Vocabulary)
            .where(
                and_(
                    Vocabulary.language == language,
                    or_(
                        Vocabulary.word.ilike(f"%{query}%"),
                        func.similarity(Vocabulary.word, query) > 0.3
                    )
                )
            )
            .order_by(func.similarity(Vocabulary.word, query).desc())
            .limit(limit)
            .offset(offset)
        )
        
        vocabularies = result.scalars().all()
        return [await self._vocab_to_dict(v) for v in vocabularies]
    
    async def get_synonyms(
        self,
        vocab_id: UUID,
        min_strength: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        获取词汇的同义词
        
        Args:
            vocab_id: 词汇ID
            min_strength: 最小关联强度
            
        Returns:
            同义词列表
        """
        # 查询双向同义词关系
        result = await self.db.execute(
            select(Vocabulary, SynonymRelation.relation_strength)
            .join(
                SynonymRelation,
                or_(
                    and_(
                        SynonymRelation.vocabulary_id_1 == vocab_id,
                        Vocabulary.id == SynonymRelation.vocabulary_id_2
                    ),
                    and_(
                        SynonymRelation.vocabulary_id_2 == vocab_id,
                        Vocabulary.id == SynonymRelation.vocabulary_id_1
                    )
                )
            )
            .where(SynonymRelation.relation_strength >= min_strength)
            .order_by(SynonymRelation.relation_strength.desc())
        )
        
        synonyms = []
        for vocab, strength in result.all():
            vocab_dict = await self._vocab_to_dict(vocab)
            vocab_dict["relation_strength"] = strength
            synonyms.append(vocab_dict)
            
        return synonyms
    
    async def add_synonym_relation(
        self,
        vocab_id_1: UUID,
        vocab_id_2: UUID,
        relation_strength: float = 1.0
    ) -> bool:
        """
        添加同义词关系
        
        Args:
            vocab_id_1: 词汇1 ID
            vocab_id_2: 词汇2 ID
            relation_strength: 关联强度 (0-1)
            
        Returns:
            是否成功
        """
        try:
            relation = SynonymRelation(
                vocabulary_id_1=vocab_id_1,
                vocabulary_id_2=vocab_id_2,
                relation_strength=relation_strength
            )
            self.db.add(relation)
            await self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to add synonym relation: {e}")
            await self.db.rollback()
            return False
    
    async def get_vocabulary_by_tags(
        self,
        tag_names: List[str],
        language: str = "en",
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        根据标签获取词汇
        
        Args:
            tag_names: 标签名称列表
            language: 语言代码
            limit: 返回数量限制
            
        Returns:
            词汇列表
        """
        result = await self.db.execute(
            select(Vocabulary)
            .join(vocabulary_tags)
            .join(Tag)
            .where(
                and_(
                    Vocabulary.language == language,
                    Tag.name.in_(tag_names)
                )
            )
            .limit(limit)
        )
        
        vocabularies = result.scalars().all()
        return [await self._vocab_to_dict(v) for v in vocabularies]
    
    async def _vocab_to_dict(
        self, 
        vocab: Vocabulary
    ) -> Dict[str, Any]:
        """
        将词汇模型转换为字典
        
        Args:
            vocab: 词汇模型
            
        Returns:
            词汇字典
        """
        # 获取定义
        definitions = []
        for def_ in vocab.definitions:
            definitions.append({
                "id": str(def_.id),
                "definition": def_.definition,
                "language": def_.language,
                "example_sentence": def_.example_sentence,
                "example_translation": def_.example_translation,
                "source": def_.source
            })
        
        # 获取标签
        tags = [tag.name for tag in vocab.tags]
        
        return {
            "id": str(vocab.id),
            "word": vocab.word,
            "language": vocab.language,
            "pronunciation": vocab.pronunciation,
            "part_of_speech": vocab.part_of_speech,
            "difficulty_level": vocab.difficulty_level,
            "frequency_rank": vocab.frequency_rank,
            "definitions": definitions,
            "tags": tags,
            "created_at": vocab.created_at.isoformat() if vocab.created_at else None,
            "updated_at": vocab.updated_at.isoformat() if vocab.updated_at else None
        }
    
    async def bulk_import_vocabulary(
        self,
        vocabulary_data: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        批量导入词汇
        
        Args:
            vocabulary_data: 词汇数据列表
            
        Returns:
            导入统计信息
        """
        stats = {"success": 0, "failed": 0, "errors": []}
        
        for data in vocabulary_data:
            try:
                # 创建词汇
                vocab = Vocabulary(
                    word=data["word"],
                    language=data.get("language", "en"),
                    pronunciation=data.get("pronunciation"),
                    part_of_speech=data.get("part_of_speech"),
                    difficulty_level=data.get("difficulty_level", 1),
                    frequency_rank=data.get("frequency_rank")
                )
                self.db.add(vocab)
                await self.db.flush()  # 获取ID
                
                # 添加定义
                for def_data in data.get("definitions", []):
                    definition = VocabularyDefinition(
                        vocabulary_id=vocab.id,
                        definition=def_data["definition"],
                        language=def_data.get("language", "zh"),
                        example_sentence=def_data.get("example_sentence"),
                        example_translation=def_data.get("example_translation"),
                        source=def_data.get("source")
                    )
                    self.db.add(definition)
                
                stats["success"] += 1
                
            except Exception as e:
                stats["failed"] += 1
                stats["errors"].append({
                    "word": data.get("word"),
                    "error": str(e)
                })
                logger.error(f"Failed to import vocabulary {data.get('word')}: {e}")
        
        await self.db.commit()
        return stats
