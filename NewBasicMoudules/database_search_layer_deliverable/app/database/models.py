# =====================================================
# AI外语学习系统 - 数据库模型
# 版本: 1.0.0
# 描述: SQLAlchemy ORM模型定义
# =====================================================

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text,
    ForeignKey, Table, UniqueConstraint, CheckConstraint,
    create_engine, select
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

Base = declarative_base()

# -----------------------------------------------------
# 关联表
# -----------------------------------------------------

# 词汇标签关联表
vocabulary_tags = Table(
    'vocabulary_tags',
    Base.metadata,
    Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column('vocabulary_id', UUID(as_uuid=True), ForeignKey('vocabulary.id', ondelete='CASCADE')),
    Column('tag_id', UUID(as_uuid=True), ForeignKey('tags.id', ondelete='CASCADE')),
    Column('created_at', DateTime(timezone=True), default=func.now()),
    UniqueConstraint('vocabulary_id', 'tag_id', name='uix_vocab_tag')
)


# -----------------------------------------------------
# 模型定义
# -----------------------------------------------------

class User(Base):
    """用户表"""
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(100))
    avatar_url = Column(String(500))
    native_language = Column(String(10), default='zh')
    learning_language = Column(String(10), default='en')
    proficiency_level = Column(String(20), default='beginner')
    daily_goal_minutes = Column(Integer, default=30)
    streak_days = Column(Integer, default=0)
    total_learning_minutes = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    last_login_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # 关联
    learning_progress = relationship("UserVocabularyProgress", back_populates="user")
    learning_sessions = relationship("LearningSession", back_populates="user")
    pronunciation_practices = relationship("PronunciationPractice", back_populates="user")
    ai_conversations = relationship("AIConversation", back_populates="user")


class Vocabulary(Base):
    """词汇表"""
    __tablename__ = 'vocabulary'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    word = Column(String(255), nullable=False)
    language = Column(String(10), nullable=False)
    pronunciation = Column(String(255))
    part_of_speech = Column(String(50))
    difficulty_level = Column(Integer, default=1)
    frequency_rank = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('word', 'language', name='uix_word_language'),
        CheckConstraint('difficulty_level BETWEEN 1 AND 5', name='check_difficulty')
    )
    
    # 关联
    definitions = relationship("VocabularyDefinition", back_populates="vocabulary", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=vocabulary_tags, back_populates="vocabularies")
    synonyms_1 = relationship("SynonymRelation", foreign_keys="SynonymRelation.vocabulary_id_1", back_populates="vocab_1")
    synonyms_2 = relationship("SynonymRelation", foreign_keys="SynonymRelation.vocabulary_id_2", back_populates="vocab_2")
    learning_progress = relationship("UserVocabularyProgress", back_populates="vocabulary")


class VocabularyDefinition(Base):
    """词汇定义表"""
    __tablename__ = 'vocabulary_definitions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vocabulary_id = Column(UUID(as_uuid=True), ForeignKey('vocabulary.id', ondelete='CASCADE'), nullable=False)
    definition = Column(Text, nullable=False)
    language = Column(String(10), nullable=False)
    example_sentence = Column(Text)
    example_translation = Column(Text)
    source = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # 关联
    vocabulary = relationship("Vocabulary", back_populates="definitions")


class SynonymRelation(Base):
    """同义词关系表"""
    __tablename__ = 'synonym_relations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vocabulary_id_1 = Column(UUID(as_uuid=True), ForeignKey('vocabulary.id', ondelete='CASCADE'), nullable=False)
    vocabulary_id_2 = Column(UUID(as_uuid=True), ForeignKey('vocabulary.id', ondelete='CASCADE'), nullable=False)
    relation_strength = Column(Integer, default=100)  # 0-100
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    __table_args__ = (
        UniqueConstraint('vocabulary_id_1', 'vocabulary_id_2', name='uix_synonym_pair'),
        CheckConstraint('relation_strength BETWEEN 0 AND 100', name='check_strength')
    )
    
    # 关联
    vocab_1 = relationship("Vocabulary", foreign_keys=[vocabulary_id_1], back_populates="synonyms_1")
    vocab_2 = relationship("Vocabulary", foreign_keys=[vocabulary_id_2], back_populates="synonyms_2")


class Tag(Base):
    """标签表"""
    __tablename__ = 'tags'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    language = Column(String(10), nullable=False)
    description = Column(Text)
    color = Column(String(7), default='#3498db')
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('name', 'category', 'language', name='uix_tag_name_cat_lang'),
    )
    
    # 关联
    vocabularies = relationship("Vocabulary", secondary=vocabulary_tags, back_populates="tags")


class LearningSession(Base):
    """学习会话表"""
    __tablename__ = 'learning_sessions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    session_type = Column(String(50), nullable=False)
    started_at = Column(DateTime(timezone=True), default=func.now())
    ended_at = Column(DateTime(timezone=True))
    duration_minutes = Column(Integer)
    score = Column(Integer)
    feedback = Column(Text)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # 关联
    user = relationship("User", back_populates="learning_sessions")


class UserVocabularyProgress(Base):
    """用户词汇学习进度表"""
    __tablename__ = 'user_vocabulary_progress'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    vocabulary_id = Column(UUID(as_uuid=True), ForeignKey('vocabulary.id', ondelete='CASCADE'), nullable=False)
    status = Column(String(20), default='new')  # new, learning, review, mastered
    mastery_level = Column(Integer, default=0)  # 0-100
    review_count = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    incorrect_count = Column(Integer, default=0)
    last_reviewed_at = Column(DateTime(timezone=True))
    next_review_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('user_id', 'vocabulary_id', name='uix_user_vocab'),
        CheckConstraint("status IN ('new', 'learning', 'review', 'mastered')", name='check_status'),
        CheckConstraint('mastery_level BETWEEN 0 AND 100', name='check_mastery')
    )
    
    # 关联
    user = relationship("User", back_populates="learning_progress")
    vocabulary = relationship("Vocabulary", back_populates="learning_progress")


class PronunciationPractice(Base):
    """发音练习记录表"""
    __tablename__ = 'pronunciation_practice'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    vocabulary_id = Column(UUID(as_uuid=True), ForeignKey('vocabulary.id', ondelete='SET NULL'))
    audio_url = Column(String(500))
    recognized_text = Column(Text)
    accuracy_score = Column(Integer)  # 0-100
    fluency_score = Column(Integer)
    completeness_score = Column(Integer)
    pronunciation_score = Column(Integer)
    practiced_at = Column(DateTime(timezone=True), default=func.now())
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # 关联
    user = relationship("User", back_populates="pronunciation_practices")


class AIConversation(Base):
    """AI对话记录表"""
    __tablename__ = 'ai_conversations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    message_role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    audio_url = Column(String(500))
    emotion_analysis = Column(JSONB)
    grammar_feedback = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # 关联
    user = relationship("User", back_populates="ai_conversations")


# -----------------------------------------------------
# 数据库连接管理
# -----------------------------------------------------

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self):
        """获取数据库会话"""
        return self.SessionLocal()
    
    def close(self):
        """关闭数据库连接"""
        self.engine.dispose()


# 便捷函数
def get_db_manager(database_url: str) -> DatabaseManager:
    """创建数据库管理器实例"""
    return DatabaseManager(database_url)


# 异步数据库支持
try:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    ASYNC_SUPPORT = True
except ImportError:
    ASYNC_SUPPORT = False

# 全局异步引擎和会话工厂
_async_engine = None
_async_session_factory = None


def init_async_db(database_url: str):
    """
    初始化异步数据库连接
    
    Args:
        database_url: 数据库连接URL，需要是异步格式
                     例如: postgresql+asyncpg://user:pass@localhost/db
    """
    global _async_engine, _async_session_factory
    
    if not ASYNC_SUPPORT:
        raise ImportError("Async SQLAlchemy support not available. "
                         "Install with: pip install sqlalchemy[asyncpg]")
    
    # 转换同步URL为异步URL
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    _async_engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
        echo=False
    )
    
    _async_session_factory = async_sessionmaker(
        _async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )


async def get_async_session() -> AsyncSession:
    """
    获取异步数据库会话（依赖注入使用）
    
    Yields:
        AsyncSession: 异步数据库会话
    """
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_async_db first.")
    
    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables_async(database_url: str):
    """
    异步创建所有表
    
    Args:
        database_url: 数据库连接URL
    """
    if not ASYNC_SUPPORT:
        raise ImportError("Async SQLAlchemy support not available.")
    
    # 转换同步URL为异步URL
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    engine = create_async_engine(database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
