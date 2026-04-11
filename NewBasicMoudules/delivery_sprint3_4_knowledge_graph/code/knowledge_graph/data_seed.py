"""
种子数据 - 初始化知识图谱

学习要点:
- 种子数据用于演示和测试
- 实际项目应从LLM生成结果导入
"""

from .models import WordRelation, RelationType


# 基础词汇关系数据 - 用于演示和测试
# 包含验收标准所需的关键数据

SEED_RELATIONS = [
    # ============ 验收标准关键数据 ============
    # "unhappy" 能召回 "happy" (反义词)
    WordRelation(source="unhappy", target="happy", relation_type=RelationType.ANTONYM, strength=0.95),
    WordRelation(source="happy", target="unhappy", relation_type=RelationType.ANTONYM, strength=0.95),
    
    # "unhappy" 能召回 "unfortunate" (近义词)
    WordRelation(source="unhappy", target="unfortunate", relation_type=RelationType.SYNONYM, strength=0.8),
    WordRelation(source="unfortunate", target="unhappy", relation_type=RelationType.SYNONYM, strength=0.8),
    
    # ============ 反义词对 ============
    WordRelation(source="happy", target="sad", relation_type=RelationType.ANTONYM, strength=1.0),
    WordRelation(source="sad", target="happy", relation_type=RelationType.ANTONYM, strength=1.0),
    WordRelation(source="good", target="bad", relation_type=RelationType.ANTONYM, strength=1.0),
    WordRelation(source="bad", target="good", relation_type=RelationType.ANTONYM, strength=1.0),
    WordRelation(source="big", target="small", relation_type=RelationType.ANTONYM, strength=1.0),
    WordRelation(source="small", target="big", relation_type=RelationType.ANTONYM, strength=1.0),
    WordRelation(source="hot", target="cold", relation_type=RelationType.ANTONYM, strength=1.0),
    WordRelation(source="cold", target="hot", relation_type=RelationType.ANTONYM, strength=1.0),
    WordRelation(source="fast", target="slow", relation_type=RelationType.ANTONYM, strength=1.0),
    WordRelation(source="slow", target="fast", relation_type=RelationType.ANTONYM, strength=1.0),
    WordRelation(source="easy", target="difficult", relation_type=RelationType.ANTONYM, strength=1.0),
    WordRelation(source="difficult", target="easy", relation_type=RelationType.ANTONYM, strength=1.0),
    WordRelation(source="love", target="hate", relation_type=RelationType.ANTONYM, strength=1.0),
    WordRelation(source="hate", target="love", relation_type=RelationType.ANTONYM, strength=1.0),
    WordRelation(source="success", target="failure", relation_type=RelationType.ANTONYM, strength=1.0),
    WordRelation(source="failure", target="success", relation_type=RelationType.ANTONYM, strength=1.0),
    WordRelation(source="begin", target="end", relation_type=RelationType.ANTONYM, strength=1.0),
    WordRelation(source="end", target="begin", relation_type=RelationType.ANTONYM, strength=1.0),
    
    # ============ 同义词对 ============
    WordRelation(source="happy", target="joyful", relation_type=RelationType.SYNONYM, strength=0.9),
    WordRelation(source="joyful", target="happy", relation_type=RelationType.SYNONYM, strength=0.9),
    WordRelation(source="happy", target="cheerful", relation_type=RelationType.SYNONYM, strength=0.85),
    WordRelation(source="cheerful", target="happy", relation_type=RelationType.SYNONYM, strength=0.85),
    WordRelation(source="sad", target="unhappy", relation_type=RelationType.SYNONYM, strength=0.9),
    WordRelation(source="unhappy", target="sad", relation_type=RelationType.SYNONYM, strength=0.9),
    WordRelation(source="sad", target="sorrowful", relation_type=RelationType.SYNONYM, strength=0.85),
    WordRelation(source="sorrowful", target="sad", relation_type=RelationType.SYNONYM, strength=0.85),
    WordRelation(source="unfortunate", target="sad", relation_type=RelationType.SYNONYM, strength=0.75),
    WordRelation(source="sad", target="unfortunate", relation_type=RelationType.SYNONYM, strength=0.75),
    WordRelation(source="big", target="large", relation_type=RelationType.SYNONYM, strength=0.95),
    WordRelation(source="large", target="big", relation_type=RelationType.SYNONYM, strength=0.95),
    WordRelation(source="small", target="tiny", relation_type=RelationType.SYNONYM, strength=0.85),
    WordRelation(source="tiny", target="small", relation_type=RelationType.SYNONYM, strength=0.85),
    WordRelation(source="important", target="significant", relation_type=RelationType.SYNONYM, strength=0.9),
    WordRelation(source="significant", target="important", relation_type=RelationType.SYNONYM, strength=0.9),
    WordRelation(source="beautiful", target="pretty", relation_type=RelationType.SYNONYM, strength=0.85),
    WordRelation(source="pretty", target="beautiful", relation_type=RelationType.SYNONYM, strength=0.85),
    WordRelation(source="begin", target="start", relation_type=RelationType.SYNONYM, strength=0.95),
    WordRelation(source="start", target="begin", relation_type=RelationType.SYNONYM, strength=0.95),
    
    # ============ 同根词 (词根词缀) ============
    WordRelation(source="happy", target="happiness", relation_type=RelationType.COGNATE, strength=1.0),
    WordRelation(source="happiness", target="happy", relation_type=RelationType.COGNATE, strength=1.0),
    WordRelation(source="happy", target="happily", relation_type=RelationType.COGNATE, strength=1.0),
    WordRelation(source="happily", target="happy", relation_type=RelationType.COGNATE, strength=1.0),
    WordRelation(source="sad", target="sadness", relation_type=RelationType.COGNATE, strength=1.0),
    WordRelation(source="sadness", target="sad", relation_type=RelationType.COGNATE, strength=1.0),
    WordRelation(source="sad", target="sadly", relation_type=RelationType.COGNATE, strength=1.0),
    WordRelation(source="sadly", target="sad", relation_type=RelationType.COGNATE, strength=1.0),
    WordRelation(source="success", target="successful", relation_type=RelationType.COGNATE, strength=1.0),
    WordRelation(source="successful", target="success", relation_type=RelationType.COGNATE, strength=1.0),
    WordRelation(source="success", target="successfully", relation_type=RelationType.COGNATE, strength=1.0),
    WordRelation(source="successfully", target="success", relation_type=RelationType.COGNATE, strength=1.0),
    WordRelation(source="beauty", target="beautiful", relation_type=RelationType.COGNATE, strength=1.0),
    WordRelation(source="beautiful", target="beauty", relation_type=RelationType.COGNATE, strength=1.0),
    WordRelation(source="beauty", target="beautifully", relation_type=RelationType.COGNATE, strength=1.0),
    WordRelation(source="beautifully", target="beauty", relation_type=RelationType.COGNATE, strength=1.0),
    WordRelation(source="importance", target="important", relation_type=RelationType.COGNATE, strength=1.0),
    WordRelation(source="important", target="importance", relation_type=RelationType.COGNATE, strength=1.0),
    WordRelation(source="different", target="difference", relation_type=RelationType.COGNATE, strength=1.0),
    WordRelation(source="difference", target="different", relation_type=RelationType.COGNATE, strength=1.0),
    
    # ============ 形近词/音近词 ============
    WordRelation(source="book", target="look", relation_type=RelationType.SIMILAR_FORM, strength=0.6),
    WordRelation(source="look", target="book", relation_type=RelationType.SIMILAR_FORM, strength=0.6),
    WordRelation(source="cat", target="cut", relation_type=RelationType.SIMILAR_FORM, strength=0.5),
    WordRelation(source="cut", target="cat", relation_type=RelationType.SIMILAR_FORM, strength=0.5),
    WordRelation(source="big", target="bag", relation_type=RelationType.SIMILAR_FORM, strength=0.5),
    WordRelation(source="bag", target="big", relation_type=RelationType.SIMILAR_FORM, strength=0.5),
]


async def seed_knowledge_graph(service):
    """
    初始化知识图谱种子数据
    
    使用方法:
        from app.knowledge_graph.data_seed import seed_knowledge_graph
        await seed_knowledge_graph(kg_service)
    """
    # 先添加词汇节点（带属性）
    vocab_data = {
        # 基础词汇 (难度1)
        "cat": ("kæt", "猫", 1, ["animal", "noun"]),
        "dog": ("dɔːɡ", "狗", 1, ["animal", "noun"]),
        "book": ("bʊk", "书", 1, ["object", "noun"]),
        "pen": ("pen", "笔", 1, ["object", "noun"]),
        "apple": ("ˈæpl", "苹果", 1, ["food", "noun"]),
        
        # 初级词汇 (难度2)
        "happy": ("ˈhæpi", "快乐的", 2, ["emotion", "adjective"]),
        "sad": ("sæd", "悲伤的", 2, ["emotion", "adjective"]),
        "good": ("ɡʊd", "好的", 2, ["quality", "adjective"]),
        "bad": ("bæd", "坏的", 2, ["quality", "adjective"]),
        "big": ("bɪɡ", "大的", 2, ["size", "adjective"]),
        "small": ("smɔːl", "小的", 2, ["size", "adjective"]),
        "school": ("skuːl", "学校", 2, ["place", "noun"]),
        "friend": ("frend", "朋友", 2, ["person", "noun"]),
        
        # 中级词汇 (难度3)
        "beautiful": ("ˈbjuːtɪfl", "美丽的", 3, ["quality", "adjective"]),
        "important": ("ɪmˈpɔːtnt", "重要的", 3, ["quality", "adjective"]),
        "different": ("ˈdɪfrənt", "不同的", 3, ["quality", "adjective"]),
        "interesting": ("ˈɪntrəstɪŋ", "有趣的", 3, ["quality", "adjective"]),
        "joyful": ("ˈdʒɔɪfl", "欢乐的", 3, ["emotion", "adjective"]),
        "cheerful": ("ˈtʃɪrfl", "愉快的", 3, ["emotion", "adjective"]),
        
        # 中高级词汇 (难度4)
        "pronunciation": ("prəˌnʌnsiˈeɪʃn", "发音", 4, ["language", "noun"]),
        "vocabulary": ("vəˈkæbjələri", "词汇", 4, ["language", "noun"]),
        "grammar": ("ˈɡræmə(r)", "语法", 4, ["language", "noun"]),
        
        # 高级词汇 (难度5-6)
        "unhappy": ("ʌnˈhæpi", "不快乐的", 3, ["emotion", "adjective", "negative"]),
        "unfortunate": ("ʌnˈfɔːtʃənət", "不幸的", 4, ["quality", "adjective", "negative"]),
        "happiness": ("ˈhæpinəs", "幸福", 3, ["emotion", "noun"]),
        "sadness": ("ˈsædnəs", "悲伤", 3, ["emotion", "noun"]),
    }
    
    print("📦 添加词汇节点...")
    for word, (phonetic, meaning, difficulty, tags) in vocab_data.items():
        await service.add_word(word, phonetic, meaning, difficulty, tags)
    
    # 再添加关系
    print("🔗 添加词汇关系...")
    result = await service.batch_import_relations(SEED_RELATIONS)
    print(f"✅ Seeded knowledge graph: {result['success']} relations imported, {result['failed']} failed")
    return result
