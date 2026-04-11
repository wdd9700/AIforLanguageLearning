# =====================================================
# AI外语学习系统 - 词汇索引管理器
# 版本: 1.0.0
# 描述: 词汇数据的ES索引管理，支持批量索引和更新
# =====================================================

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from .es_client import ElasticsearchClient
from .es_config import INDEX_NAMES

logger = logging.getLogger(__name__)


@dataclass
class VocabularyEntry:
    """词汇条目数据类"""
    id: str
    word: str
    language: str = "en"
    pronunciation: Optional[str] = None
    phonetic_us: Optional[str] = None
    phonetic_uk: Optional[str] = None
    part_of_speech: Optional[str] = None
    difficulty_level: int = 1
    frequency_rank: Optional[int] = None
    definitions: List[Dict[str, str]] = None
    definition_zh: Optional[str] = None
    definition_en: Optional[str] = None
    example_en: Optional[str] = None
    example_translation_zh: Optional[str] = None
    tags: List[str] = None
    synonyms: List[str] = None
    memory_tip: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def __post_init__(self):
        if self.definitions is None:
            self.definitions = []
        if self.tags is None:
            self.tags = []
        if self.synonyms is None:
            self.synonyms = []
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow().isoformat()
    
    def to_es_document(self) -> Dict[str, Any]:
        """转换为ES文档格式"""
        return {
            "id": self.id,
            "word": self.word,
            "language": self.language,
            "pronunciation": self.pronunciation,
            "phonetic_us": self.phonetic_us,
            "phonetic_uk": self.phonetic_uk,
            "part_of_speech": self.part_of_speech,
            "difficulty_level": self.difficulty_level,
            "frequency_rank": self.frequency_rank,
            "definitions": self.definitions,
            "definition_zh": self.definition_zh,
            "definition_en": self.definition_en,
            "example_en": self.example_en,
            "example_translation_zh": self.example_translation_zh,
            "tags": self.tags,
            "synonyms": self.synonyms,
            "memory_tip": self.memory_tip,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    def to_suggestion_document(self) -> Dict[str, Any]:
        """转换为搜索建议文档格式"""
        return {
            "word": self.word,
            "suggest": {
                "input": [self.word] + self.synonyms,
                "weight": self.frequency_rank or 100
            },
            "contexts": self.tags,
            "weight": self.frequency_rank or 100
        }


class VocabularyIndexer:
    """
    词汇索引管理器
    
    功能：
    1. 单条/批量索引词汇
    2. 索引同义词
    3. 索引搜索建议
    4. 删除词汇
    5. 更新词汇
    """
    
    def __init__(self, es_client: Optional[ElasticsearchClient] = None):
        """
        初始化索引管理器
        
        Args:
            es_client: Elasticsearch客户端
        """
        self.es = es_client
        self.vocab_index = INDEX_NAMES["vocabulary"]
        self.synonym_index = INDEX_NAMES["synonyms"]
        self.suggestion_index = INDEX_NAMES["suggestions"]
    
    async def connect(self, hosts: Optional[List[str]] = None) -> bool:
        """
        连接到Elasticsearch
        
        Args:
            hosts: ES主机列表
            
        Returns:
            是否连接成功
        """
        if self.es is None:
            self.es = ElasticsearchClient(hosts=hosts)
        return await self.es.connect()
    
    async def close(self):
        """关闭连接"""
        if self.es:
            await self.es.close()
    
    async def init_indices(self) -> Dict[str, bool]:
        """
        初始化所有索引
        
        Returns:
            各索引创建结果
        """
        if not self.es:
            raise RuntimeError("Elasticsearch client not initialized")
        return await self.es.init_indices()
    
    async def index_vocabulary(
        self,
        entry: VocabularyEntry,
        index_synonyms: bool = True,
        index_suggestion: bool = True
    ) -> bool:
        """
        索引单个词汇
        
        Args:
            entry: 词汇条目
            index_synonyms: 是否同时索引同义词
            index_suggestion: 是否同时索引搜索建议
            
        Returns:
            是否索引成功
        """
        if not self.es or not self.es.is_connected:
            logger.error("Elasticsearch not connected")
            return False
        
        try:
            # 索引词汇
            success = await self.es.index_document(
                index_name=self.vocab_index,
                document=entry.to_es_document(),
                doc_id=entry.id
            )
            
            if not success:
                return False
            
            # 索引同义词
            if index_synonyms and entry.synonyms:
                await self._index_synonyms(entry.word, entry.synonyms)
            
            # 索引搜索建议
            if index_suggestion:
                await self.es.index_document(
                    index_name=self.suggestion_index,
                    document=entry.to_suggestion_document(),
                    doc_id=entry.id
                )
            
            logger.info(f"Indexed vocabulary: {entry.word}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index vocabulary {entry.word}: {e}")
            return False
    
    async def bulk_index_vocabulary(
        self,
        entries: List[VocabularyEntry],
        batch_size: int = 1000,
        index_synonyms: bool = True,
        index_suggestions: bool = True
    ) -> Dict[str, Any]:
        """
        批量索引词汇
        
        Args:
            entries: 词汇条目列表
            batch_size: 批量大小
            index_synonyms: 是否同时索引同义词
            index_suggestions: 是否同时索引搜索建议
            
        Returns:
            批量操作结果
            {
                "success": True/False,
                "indexed": 成功索引数量,
                "errors": 错误列表,
                "synonyms_indexed": 同义词索引数量,
                "suggestions_indexed": 建议索引数量
            }
        """
        if not self.es or not self.es.is_connected:
            return {"success": False, "error": "Elasticsearch not connected"}
        
        if not entries:
            return {"success": True, "indexed": 0, "errors": []}
        
        results = {
            "success": True,
            "indexed": 0,
            "errors": [],
            "synonyms_indexed": 0,
            "suggestions_indexed": 0
        }
        
        try:
            # 准备词汇文档
            vocab_docs = []
            suggestion_docs = []
            synonym_entries = []
            
            for entry in entries:
                vocab_docs.append(entry.to_es_document())
                
                if index_suggestions:
                    suggestion_docs.append(entry.to_suggestion_document())
                
                if index_synonyms and entry.synonyms:
                    synonym_entries.append({
                        "word": entry.word,
                        "synonyms": entry.synonyms
                    })
            
            # 批量索引词汇
            vocab_result = await self.es.bulk_index(
                index_name=self.vocab_index,
                documents=vocab_docs,
                id_field="id"
            )
            
            if vocab_result["success"]:
                results["indexed"] = vocab_result["indexed"]
                results["errors"].extend(vocab_result.get("errors", []))
            else:
                results["success"] = False
                results["errors"].append(vocab_result.get("error", "Unknown error"))
                return results
            
            # 批量索引搜索建议
            if index_suggestions and suggestion_docs:
                suggestion_result = await self.es.bulk_index(
                    index_name=self.suggestion_index,
                    documents=suggestion_docs,
                    id_field="word"
                )
                if suggestion_result["success"]:
                    results["suggestions_indexed"] = suggestion_result["indexed"]
            
            # 批量索引同义词
            if index_synonyms and synonym_entries:
                synonym_docs = [
                    {
                        "word": entry["word"],
                        "synonyms": entry["synonyms"],
                        "created_at": datetime.utcnow().isoformat()
                    }
                    for entry in synonym_entries
                ]
                synonym_result = await self.es.bulk_index(
                    index_name=self.synonym_index,
                    documents=synonym_docs,
                    id_field="word"
                )
                if synonym_result["success"]:
                    results["synonyms_indexed"] = synonym_result["indexed"]
            
            logger.info(f"Bulk indexed {results['indexed']} vocabulary entries")
            return results
            
        except Exception as e:
            logger.error(f"Bulk index failed: {e}")
            results["success"] = False
            results["errors"].append(str(e))
            return results
    
    async def _index_synonyms(self, word: str, synonyms: List[str]) -> bool:
        """
        索引同义词
        
        Args:
            word: 词汇
            synonyms: 同义词列表
            
        Returns:
            是否索引成功
        """
        if not self.es or not self.es.is_connected:
            return False
        
        try:
            document = {
                "word": word,
                "synonyms": synonyms,
                "created_at": datetime.utcnow().isoformat()
            }
            
            return await self.es.index_document(
                index_name=self.synonym_index,
                document=document,
                doc_id=word
            )
        except Exception as e:
            logger.error(f"Failed to index synonyms for {word}: {e}")
            return False
    
    async def delete_vocabulary(self, vocab_id: str) -> bool:
        """
        删除词汇
        
        Args:
            vocab_id: 词汇ID
            
        Returns:
            是否删除成功
        """
        if not self.es or not self.es.is_connected:
            return False
        
        try:
            # 获取词汇信息（用于删除相关索引）
            vocab = await self.es.get_document(self.vocab_index, vocab_id)
            word = vocab.get("word") if vocab else None
            
            # 删除词汇索引
            success = await self.es.delete_document(self.vocab_index, vocab_id)
            
            # 删除搜索建议
            if word:
                await self.es.delete_document(self.suggestion_index, word)
            
            return success
        except Exception as e:
            logger.error(f"Failed to delete vocabulary {vocab_id}: {e}")
            return False
    
    async def update_vocabulary(
        self,
        vocab_id: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """
        更新词汇
        
        Args:
            vocab_id: 词汇ID
            update_data: 更新数据
            
        Returns:
            是否更新成功
        """
        if not self.es or not self.es.is_connected:
            return False
        
        try:
            # 添加更新时间
            update_data["updated_at"] = datetime.utcnow().isoformat()
            
            # 使用index_document更新（upsert）
            return await self.es.index_document(
                index_name=self.vocab_index,
                document=update_data,
                doc_id=vocab_id
            )
        except Exception as e:
            logger.error(f"Failed to update vocabulary {vocab_id}: {e}")
            return False
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """
        获取索引统计信息
        
        Returns:
            索引统计信息
        """
        if not self.es or not self.es.is_connected:
            return {"error": "Not connected"}
        
        try:
            stats = {}
            
            # 词汇索引统计
            vocab_count = await self.es.client.count(index=self.vocab_index)
            stats["vocabulary_count"] = vocab_count.get("count", 0)
            
            # 同义词索引统计
            synonym_count = await self.es.client.count(index=self.synonym_index)
            stats["synonym_count"] = synonym_count.get("count", 0)
            
            # 建议索引统计
            suggestion_count = await self.es.client.count(index=self.suggestion_index)
            stats["suggestion_count"] = suggestion_count.get("count", 0)
            
            return stats
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {"error": str(e)}


# 便捷函数
async def bulk_index_vocabulary(
    entries: List[VocabularyEntry],
    es_hosts: Optional[List[str]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    批量索引词汇的便捷函数
    
    Args:
        entries: 词汇条目列表
        es_hosts: ES主机列表
        **kwargs: 其他参数
        
    Returns:
        批量操作结果
    """
    indexer = VocabularyIndexer()
    await indexer.connect(hosts=es_hosts)
    try:
        return await indexer.bulk_index_vocabulary(entries, **kwargs)
    finally:
        await indexer.close()
