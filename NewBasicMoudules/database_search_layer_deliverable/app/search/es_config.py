# =====================================================
# AI外语学习系统 - Elasticsearch 映射配置
# 版本: 1.0.0
# 描述: ES索引映射、分词器配置和搜索设置
# =====================================================

from typing import Dict, Any

# -----------------------------------------------------
# 词汇索引映射配置
# -----------------------------------------------------
VOCABULARY_INDEX_MAPPING: Dict[str, Any] = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            # 分析器配置
            "analyzer": {
                # IK分词器 - 细粒度分词
                "ik_analyzer": {
                    "type": "custom",
                    "tokenizer": "ik_max_word"
                },
                # IK分词器 - 智能分词
                "ik_smart_analyzer": {
                    "type": "custom",
                    "tokenizer": "ik_smart"
                },
                # 拼音分析器
                "pinyin_analyzer": {
                    "type": "custom",
                    "tokenizer": "pinyin_tokenizer"
                },
                # 英文分析器（小写+词干提取）
                "english_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "english_stop",
                        "english_stemmer"
                    ]
                },
                # 模糊搜索分析器（支持拼写纠错）
                "fuzzy_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "edge_ngram_filter"
                    ]
                }
            },
            # 分词器配置
            "tokenizer": {
                "pinyin_tokenizer": {
                    "type": "pinyin",
                    "keep_separate_first_letter": False,
                    "keep_full_pinyin": True,
                    "keep_original": True,
                    "limit_first_letter_length": 16,
                    "lowercase": True,
                    "remove_duplicated_term": True
                }
            },
            # 过滤器配置
            "filter": {
                "english_stop": {
                    "type": "stop",
                    "stopwords": "_english_"
                },
                "english_stemmer": {
                    "type": "stemmer",
                    "language": "english"
                },
                "edge_ngram_filter": {
                    "type": "edge_ngram",
                    "min_gram": 2,
                    "max_gram": 10
                },
                "synonym_filter": {
                    "type": "synonym_graph",
                    "synonyms": [],  # 动态加载同义词
                    "updateable": True
                }
            }
        }
    },
    "mappings": {
        "properties": {
            # 词汇ID
            "id": {
                "type": "keyword"
            },
            # 词汇本身
            "word": {
                "type": "text",
                "analyzer": "english_analyzer",
                "search_analyzer": "english_analyzer",
                "fields": {
                    # 原始值（精确匹配）
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256
                    },
                    # 模糊搜索
                    "fuzzy": {
                        "type": "text",
                        "analyzer": "fuzzy_analyzer"
                    },
                    # 拼音搜索
                    "pinyin": {
                        "type": "text",
                        "analyzer": "pinyin_analyzer"
                    }
                }
            },
            # 语言
            "language": {
                "type": "keyword"
            },
            # 发音
            "pronunciation": {
                "type": "keyword",
                "index": False
            },
            # 词性
            "part_of_speech": {
                "type": "keyword"
            },
            # 难度等级
            "difficulty_level": {
                "type": "integer"
            },
            # 词频排名
            "frequency_rank": {
                "type": "integer"
            },
            # 中文定义
            "definition_zh": {
                "type": "text",
                "analyzer": "ik_analyzer",
                "fields": {
                    "keyword": {
                        "type": "keyword"
                    }
                }
            },
            # 英文定义
            "definition_en": {
                "type": "text",
                "analyzer": "english_analyzer"
            },
            # 例句
            "example_en": {
                "type": "text",
                "analyzer": "english_analyzer"
            },
            # 例句翻译
            "example_translation_zh": {
                "type": "text",
                "analyzer": "ik_analyzer"
            },
            # 标签
            "tags": {
                "type": "keyword"
            },
            # 同义词列表
            "synonyms": {
                "type": "keyword"
            },
            # 创建时间
            "created_at": {
                "type": "date",
                "format": "strict_date_optional_time||epoch_millis"
            },
            # 更新时间
            "updated_at": {
                "type": "date",
                "format": "strict_date_optional_time||epoch_millis"
            }
        }
    }
}

# -----------------------------------------------------
# 同义词索引映射配置
# -----------------------------------------------------
SYNONYM_INDEX_MAPPING: Dict[str, Any] = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0
    },
    "mappings": {
        "properties": {
            "word": {
                "type": "keyword"
            },
            "synonyms": {
                "type": "keyword"
            },
            "relation_strength": {
                "type": "float"
            },
            "created_at": {
                "type": "date"
            }
        }
    }
}

# -----------------------------------------------------
# 搜索建议索引映射配置
# -----------------------------------------------------
SUGGESTION_INDEX_MAPPING: Dict[str, Any] = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                "suggest_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "asciifolding"
                    ]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "word": {
                "type": "keyword"
            },
            "suggest": {
                "type": "completion",
                "analyzer": "suggest_analyzer"
            },
            "weight": {
                "type": "integer"
            },
            "contexts": {
                "type": "keyword"
            }
        }
    }
}

# -----------------------------------------------------
# 索引名称配置
# -----------------------------------------------------
INDEX_NAMES = {
    "vocabulary": "aifl_vocabulary",
    "synonyms": "aifl_synonyms",
    "suggestions": "aifl_suggestions"
}

# -----------------------------------------------------
# 搜索配置常量
# -----------------------------------------------------
SEARCH_CONFIG = {
    # 默认返回结果数
    "default_size": 20,
    # 最大返回结果数
    "max_size": 100,
    # 模糊搜索编辑距离
    "fuzzy_distance": 2,
    # 最小匹配分数
    "min_score": 0.3,
    # 高亮标签
    "highlight_pre_tag": "<mark>",
    "highlight_post_tag": "</mark>",
    # 缓存时间（秒）
    "cache_ttl": 300
}


def get_vocabulary_index_settings() -> Dict[str, Any]:
    """获取词汇索引配置"""
    return VOCABULARY_INDEX_MAPPING.copy()


def get_synonym_index_settings() -> Dict[str, Any]:
    """获取同义词索引配置"""
    return SYNONYM_INDEX_MAPPING.copy()


def get_suggestion_index_settings() -> Dict[str, Any]:
    """获取搜索建议索引配置"""
    return SUGGESTION_INDEX_MAPPING.copy()


def get_index_name(index_type: str) -> str:
    """获取索引名称"""
    return INDEX_NAMES.get(index_type, f"aifl_{index_type}")
