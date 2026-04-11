#!/usr/bin/env python3
# =====================================================
# AI外语学习系统 - 词汇数据导入脚本
# 版本: 1.0.0
# 描述: 从JSON/CSV文件批量导入词汇到PostgreSQL和Elasticsearch
# =====================================================

import argparse
import csv
import json
import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.search.vocabulary_indexer import VocabularyIndexer, VocabularyEntry
from app.search.es_client import ElasticsearchClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VocabularyImporter:
    """
    词汇数据导入器
    
    支持从JSON/CSV文件导入词汇数据到：
    1. PostgreSQL（主数据库）
    2. Elasticsearch（搜索引擎）
    """
    
    def __init__(
        self,
        db_url: Optional[str] = None,
        es_host: Optional[str] = None,
        redis_host: Optional[str] = None,
        batch_size: int = 1000
    ):
        """
        初始化导入器
        
        Args:
            db_url: PostgreSQL连接URL
            es_host: Elasticsearch主机地址
            redis_host: Redis主机地址
            batch_size: 批量插入大小
        """
        self.db_url = db_url or "postgresql://aifl_user:aifl_password@localhost:5432/aifl_db"
        self.es_host = es_host or "http://localhost:9200"
        self.redis_host = redis_host or "localhost"
        self.batch_size = batch_size
        self.db_client = None
        self.es_client = None
        self.indexer = None
    
    async def connect(self):
        """连接数据库"""
        # 连接PostgreSQL
        try:
            import asyncpg
            self.db_client = await asyncpg.connect(self.db_url)
            logger.info("Connected to PostgreSQL")
        except ImportError:
            logger.warning("asyncpg not installed, skipping PostgreSQL connection")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
        
        # 连接Elasticsearch
        try:
            self.es_client = ElasticsearchClient(hosts=[self.es_host])
            connected = await self.es_client.connect()
            if connected:
                self.indexer = VocabularyIndexer(es_client=self.es_client)
                # 初始化索引
                await self.indexer.init_indices()
                logger.info("Connected to Elasticsearch and initialized indices")
            else:
                logger.error("Failed to connect to Elasticsearch")
                self.es_client = None
        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {e}")
            self.es_client = None
    
    async def close(self):
        """关闭连接"""
        if self.db_client:
            await self.db_client.close()
        if self.es_client:
            await self.es_client.close()
    
    def parse_json_file(self, file_path: str) -> List[VocabularyEntry]:
        """
        解析JSON文件
        
        支持格式：
        {
            "vocabulary": [
                {
                    "word": "hello",
                    "pronunciation": "/həˈloʊ/",
                    "part_of_speech": "interjection",
                    "difficulty_level": 1,
                    "definitions": [
                        {"language": "zh", "definition": "你好", "example": "Hello, world!"}
                    ],
                    "tags": ["beginner", "daily"]
                }
            ]
        }
        """
        entries = []
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        vocab_list = data.get('vocabulary', data) if isinstance(data, dict) else data
        
        for item in vocab_list:
            entry = VocabularyEntry(
                word=item.get('word', ''),
                language=item.get('language', 'en'),
                pronunciation=item.get('pronunciation'),
                part_of_speech=item.get('part_of_speech'),
                difficulty_level=item.get('difficulty_level', 1),
                frequency_rank=item.get('frequency_rank'),
                definitions=item.get('definitions', []),
                tags=item.get('tags', []),
                synonyms=item.get('synonyms', [])
            )
            entries.append(entry)
        
        logger.info(f"Parsed {len(entries)} entries from JSON file")
        return entries
    
    def parse_csv_file(self, file_path: str) -> List[VocabularyEntry]:
        """
        解析CSV文件
        
        支持列：word, pronunciation, part_of_speech, difficulty_level, 
               definition_zh, definition_en, example_en, tags
        """
        entries = []
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                definitions = []
                if row.get('definition_zh'):
                    definitions.append({
                        'language': 'zh',
                        'definition': row['definition_zh'],
                        'example': row.get('example_en', '')
                    })
                if row.get('definition_en'):
                    definitions.append({
                        'language': 'en',
                        'definition': row['definition_en'],
                        'example': row.get('example_en', '')
                    })
                
                tags = row.get('tags', '').split(',') if row.get('tags') else []
                synonyms = row.get('synonyms', '').split(',') if row.get('synonyms') else []
                
                entry = VocabularyEntry(
                    id=str(uuid.uuid4()),
                    word=row.get('word', ''),
                    language=row.get('language', 'en'),
                    pronunciation=row.get('pronunciation'),
                    part_of_speech=row.get('part_of_speech'),
                    difficulty_level=int(row.get('difficulty_level', 1)),
                    frequency_rank=int(row['frequency_rank']) if row.get('frequency_rank') else None,
                    definitions=definitions,
                    tags=[t.strip() for t in tags if t.strip()],
                    synonyms=[s.strip() for s in synonyms if s.strip()]
                )
                entries.append(entry)
        
        logger.info(f"Parsed {len(entries)} entries from CSV file")
        return entries
    
    async def import_to_postgres(self, entries: List[VocabularyEntry]) -> int:
        """
        导入词汇到PostgreSQL
        
        Returns:
            导入的词汇数量
        """
        if not self.db_client:
            logger.warning("PostgreSQL not connected, skipping")
            return 0
        
        imported = 0
        
        try:
            for i in range(0, len(entries), self.batch_size):
                batch = entries[i:i + self.batch_size]
                
                async with self.db_client.transaction():
                    for entry in batch:
                        # 插入词汇
                        vocab_id = await self.db_client.fetchval(
                            """
                            INSERT INTO vocabulary (word, language, pronunciation, 
                                                  part_of_speech, difficulty_level, frequency_rank)
                            VALUES ($1, $2, $3, $4, $5, $6)
                            ON CONFLICT (word, language) DO UPDATE SET
                                pronunciation = EXCLUDED.pronunciation,
                                part_of_speech = EXCLUDED.part_of_speech,
                                difficulty_level = EXCLUDED.difficulty_level,
                                frequency_rank = EXCLUDED.frequency_rank,
                                updated_at = CURRENT_TIMESTAMP
                            RETURNING id
                            """,
                            entry.word, entry.language, entry.pronunciation,
                            entry.part_of_speech, entry.difficulty_level, entry.frequency_rank
                        )
                        
                        # 插入定义
                        for def_item in entry.definitions:
                            await self.db_client.execute(
                                """
                                INSERT INTO vocabulary_definitions 
                                (vocabulary_id, definition, language, example_sentence)
                                VALUES ($1, $2, $3, $4)
                                ON CONFLICT DO NOTHING
                                """,
                                vocab_id,
                                def_item.get('definition', ''),
                                def_item.get('language', 'en'),
                                def_item.get('example', '')
                            )
                        
                        # 处理标签
                        for tag_name in entry.tags:
                            tag_id = await self.db_client.fetchval(
                                """
                                INSERT INTO tags (name, category, language)
                                VALUES ($1, 'imported', $2)
                                ON CONFLICT (name, category, language) DO UPDATE SET
                                    name = EXCLUDED.name
                                RETURNING id
                                """,
                                tag_name, entry.language
                            )
                            
                            await self.db_client.execute(
                                """
                                INSERT INTO vocabulary_tags (vocabulary_id, tag_id)
                                VALUES ($1, $2)
                                ON CONFLICT DO NOTHING
                                """,
                                vocab_id, tag_id
                            )
                        
                        imported += 1
                
                logger.info(f"Imported {imported}/{len(entries)} entries to PostgreSQL")
                
        except Exception as e:
            logger.error(f"Error importing to PostgreSQL: {e}")
            raise
        
        return imported
    
    async def import_to_elasticsearch(self, entries: List[VocabularyEntry]) -> int:
        """
        导入词汇到Elasticsearch
        
        Returns:
            导入的词汇数量
        """
        if not self.indexer:
            logger.warning("Elasticsearch not connected, skipping")
            return 0
        
        try:
            # 使用VocabularyIndexer批量索引
            result = await self.indexer.bulk_index_vocabulary(
                entries=entries,
                batch_size=self.batch_size,
                index_synonyms=True,
                index_suggestions=True
            )
            
            if result["success"]:
                imported = result["indexed"]
                logger.info(f"Imported {imported} entries to Elasticsearch")
                logger.info(f"Indexed {result.get('synonyms_indexed', 0)} synonym entries")
                logger.info(f"Indexed {result.get('suggestions_indexed', 0)} suggestion entries")
                return imported
            else:
                logger.error(f"Bulk index failed: {result.get('errors', [])}")
                return 0
                
        except Exception as e:
            logger.error(f"Error importing to Elasticsearch: {e}")
            raise
    
    async def import_file(self, file_path: str, file_type: Optional[str] = None):
        """
        导入文件
        
        Args:
            file_path: 文件路径
            file_type: 文件类型（json/csv），自动检测
        """
        path = Path(file_path)
        
        if not file_type:
            file_type = path.suffix.lower().lstrip('.')
        
        # 解析文件
        if file_type == 'json':
            entries = self.parse_json_file(file_path)
        elif file_type == 'csv':
            entries = self.parse_csv_file(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        if not entries:
            logger.warning("No entries found in file")
            return
        
        # 连接数据库
        await self.connect()
        
        try:
            # 导入到PostgreSQL
            pg_count = await self.import_to_postgres(entries)
            logger.info(f"Imported {pg_count} entries to PostgreSQL")
            
            # 导入到Elasticsearch
            es_count = await self.import_to_elasticsearch(entries)
            logger.info(f"Imported {es_count} entries to Elasticsearch")
            
        finally:
            await self.close()


def create_sample_data(output_path: str, count: int = 100):
    """创建示例词汇数据文件"""
    sample_words = [
        {
            "word": "hello",
            "pronunciation": "/həˈloʊ/",
            "part_of_speech": "interjection",
            "difficulty_level": 1,
            "definitions": [
                {"language": "zh", "definition": "你好；喂", "example": "Hello, how are you?"},
                {"language": "en", "definition": "used as a greeting", "example": "Hello, nice to meet you."}
            ],
            "tags": ["beginner", "daily"]
        },
        {
            "word": "world",
            "pronunciation": "/wɜːrld/",
            "part_of_speech": "noun",
            "difficulty_level": 1,
            "definitions": [
                {"language": "zh", "definition": "世界；地球", "example": "The world is beautiful."},
                {"language": "en", "definition": "the earth and all its countries", "example": "He wants to travel the world."}
            ],
            "tags": ["beginner", "daily"]
        },
        {
            "word": "computer",
            "pronunciation": "/kəmˈpjuːtər/",
            "part_of_speech": "noun",
            "difficulty_level": 2,
            "definitions": [
                {"language": "zh", "definition": "计算机；电脑", "example": "I use a computer for work."},
                {"language": "en", "definition": "an electronic device for processing data", "example": "She bought a new computer."}
            ],
            "tags": ["intermediate", "technology"]
        }
    ]
    
    data = {"vocabulary": sample_words[:count] if count <= len(sample_words) else sample_words}
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Created sample data file: {output_path}")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Import vocabulary data')
    parser.add_argument('file', help='Input file path (JSON or CSV)')
    parser.add_argument('--type', choices=['json', 'csv'], help='File type (auto-detect if not specified)')
    parser.add_argument('--db-url', help='PostgreSQL connection URL')
    parser.add_argument('--es-host', help='Elasticsearch host')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for import')
    parser.add_argument('--create-sample', action='store_true', help='Create sample data file')
    
    args = parser.parse_args()
    
    if args.create_sample:
        create_sample_data(args.file)
        return
    
    importer = VocabularyImporter(
        db_url=args.db_url,
        es_host=args.es_host,
        batch_size=args.batch_size
    )
    
    await importer.import_file(args.file, args.type)


if __name__ == '__main__':
    asyncio.run(main())
