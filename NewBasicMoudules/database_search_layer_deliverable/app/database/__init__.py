# =====================================================
# AI外语学习系统 - 数据库模块
# 版本: 1.0.0
# =====================================================

from .models import (
    Base,
    User,
    Vocabulary,
    VocabularyDefinition,
    SynonymRelation,
    Tag,
    LearningSession,
    UserVocabularyProgress,
    PronunciationPractice,
    AIConversation,
    vocabulary_tags,
    DatabaseManager,
    get_db_manager
)

__all__ = [
    "Base",
    "User",
    "Vocabulary",
    "VocabularyDefinition",
    "SynonymRelation",
    "Tag",
    "LearningSession",
    "UserVocabularyProgress",
    "PronunciationPractice",
    "AIConversation",
    "vocabulary_tags",
    "DatabaseManager",
    "get_db_manager"
]
