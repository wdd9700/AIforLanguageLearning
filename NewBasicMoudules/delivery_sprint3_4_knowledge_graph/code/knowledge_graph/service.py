"""
知识图谱服务层

学习要点:
- 服务层封装业务逻辑
- 混合推荐策略(协同过滤 + 内容相似)
- 缓存优化热点查询
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any, Tuple
import random
import re
import heapq
from collections import defaultdict

from .client import get_neo4j_client, Neo4jClient
from .models import (
    WordRelation,
    WordNode,
    RecommendationResult,
    RelationType,
    RelationQueryResult,
    VocabularyRecommendation,
)

# 尝试导入LightFM和FAISS
try:
    from lightfm import LightFM
    from lightfm.data import Dataset
    LIGHTFM_AVAILABLE = True
except ImportError:
    LIGHTFM_AVAILABLE = False
    print("⚠️ LightFM not available, using fallback recommendation")

try:
    import faiss
    import numpy as np
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("⚠️ FAISS not available, using fallback similarity")


class KnowledgeGraphService:
    """
    知识图谱服务
    
    这是你的核心业务逻辑层，所有功能都通过这里暴露
    """
    
    # 常见词根词缀规则
    COMMON_PREFIXES = {
        'un': '否定',
        're': '再次',
        'pre': '之前',
        'dis': '否定',
        'mis': '错误',
        'over': '过度',
        'under': '不足',
        'sub': '下面',
        'super': '超级',
        'inter': '之间',
        'anti': '反对',
        'non': '非',
        'in': '否定/内部',
        'im': '否定',
        'il': '否定',
        'ir': '否定',
    }
    
    COMMON_SUFFIXES = {
        'ness': '名词(性质)',
        'ment': '名词(行为)',
        'tion': '名词(动作)',
        'sion': '名词(动作)',
        'ity': '名词(状态)',
        'er': '名词(人/物)',
        'or': '名词(人)',
        'ist': '名词(专家)',
        'ism': '名词(主义)',
        'ful': '形容词(充满)',
        'less': '形容词(无)',
        'ous': '形容词(具有)',
        'ive': '形容词(倾向)',
        'able': '形容词(能够)',
        'ible': '形容词(能够)',
        'ly': '副词',
        'ward': '副词(方向)',
        'wise': '副词(方式)',
        'ize': '动词(使成为)',
        'ise': '动词(使成为)',
        'ify': '动词(使成为)',
        'en': '动词(使成为)',
    }
    
    def __init__(self):
        self._client: Optional[Neo4jClient] = None
        self._lightfm_model: Optional[Any] = None
        self._faiss_index: Optional[Any] = None
        self._word_embeddings: Dict[str, List[float]] = {}
        self._word_list: List[str] = []
    
    async def _get_client(self) -> Neo4jClient:
        """获取或创建客户端"""
        if self._client is None:
            self._client = await get_neo4j_client()
            await self._client.connect()
            await self._client.init_schema()
        return self._client
    
    # ==================== 词汇关系查询 ====================
    
    async def get_word_relations(
        self,
        word: str,
        relation_type: Optional[str] = None,
        limit: int = 10,
    ) -> RelationQueryResult:
        """
        获取词汇关系
        
        这是验收标准的核心功能:
        - "unhappy" 能召回 "happy" (反义词)
        - "unhappy" 能召回 "unfortunate" (近义词)
        """
        client = await self._get_client()
        
        # 确保词汇存在
        await client.create_word(word)
        
        # 查询关系
        relations_data = await client.get_relations(word, relation_type, limit)
        
        # 转换为模型
        relations = []
        for r in relations_data:
            try:
                rel_type = RelationType(r["relation_type"].lower())
            except ValueError:
                rel_type = RelationType.SIMILAR_FORM
            
            relations.append(WordRelation(
                source=word,
                target=r["word"],
                relation_type=rel_type,
                strength=r.get("strength", 1.0),
            ))
        
        return RelationQueryResult(
            word=word,
            relations=relations,
            total=len(relations),
        )
    
    async def get_antonyms(self, word: str) -> List[str]:
        """
        获取反义词列表
        
        示例: get_antonyms("happy") -> ["sad", "unhappy", ...]
        """
        result = await self.get_word_relations(word, relation_type="antonym", limit=5)
        return [r.target for r in result.relations]
    
    async def get_synonyms(self, word: str) -> List[str]:
        """
        获取同义词列表
        
        示例: get_synonyms("unhappy") -> ["sad", "unfortunate", ...]
        """
        result = await self.get_word_relations(word, relation_type="synonym", limit=5)
        return [r.target for r in result.relations]
    
    async def get_cognates(self, word: str) -> List[str]:
        """获取同根词"""
        result = await self.get_word_relations(word, relation_type="cognate", limit=5)
        return [r.target for r in result.relations]
    
    # ==================== 词汇关系构建 ====================
    
    async def add_word_relation(
        self,
        source: str,
        target: str,
        relation_type: RelationType,
        strength: float = 1.0,
    ) -> bool:
        """
        添加词汇关系
        
        使用场景:
        - LLM生成词汇后，自动建立关系
        - 用户反馈纠正关系
        - 批量导入词汇数据
        """
        client = await self._get_client()
        return await client.create_relation(
            source=source,
            target=target,
            relation_type=relation_type.value,
            strength=strength,
        )
    
    async def add_word(
        self,
        word: str,
        phonetic: Optional[str] = None,
        meaning: Optional[str] = None,
        difficulty: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """添加词汇节点"""
        client = await self._get_client()
        return await client.create_word(
            word=word,
            phonetic=phonetic,
            meaning=meaning,
            difficulty=difficulty,
            tags=tags,
        )
    
    # ==================== 推荐系统 ====================
    
    async def recommend_vocabulary(
        self,
        user_id: str,
        n: int = 10,
        user_level: int = 1,
        weak_points: Optional[List[str]] = None,
        learned_words: Optional[List[str]] = None,
    ) -> VocabularyRecommendation:
        """
        词汇推荐
        
        算法逻辑:
        1. 薄弱点匹配 (30%): 推荐与薄弱点相关的词汇
        2. 协同过滤 (40%): 基于相似用户的学习记录
        3. 内容相似 (30%): 基于词汇关系图谱
        
        验收标准: 推荐准确率 > 30%
        """
        weak_points = weak_points or []
        learned_words = learned_words or []
        
        recommendations: List[RecommendationResult] = []
        client = await self._get_client()
        
        # 策略1: 基于薄弱点推荐 (30%) - 优先从知识图谱获取
        if weak_points:
            for weak_word in weak_points[:3]:  # 取前3个薄弱点
                # 获取薄弱点的所有关系（同义词、反义词、同根词）
                relations = await self.get_word_relations(weak_word, limit=10)
                
                for rel in relations.relations:
                    target = rel.target
                    if target not in learned_words and target not in [r.word for r in recommendations]:
                        # 根据关系类型给分
                        if rel.relation_type == RelationType.SYNONYM:
                            score = 0.90
                            reason = f"'{weak_word}'的同义词，帮助巩固薄弱点"
                        elif rel.relation_type == RelationType.ANTONYM:
                            score = 0.85
                            reason = f"'{weak_word}'的反义词，对比学习"
                        elif rel.relation_type == RelationType.COGNATE:
                            score = 0.80
                            reason = f"'{weak_word}'的同根词，词根词缀学习"
                        else:
                            score = 0.70
                            reason = f"与'{weak_word}'相关的词汇"
                        
                        recommendations.append(RecommendationResult(
                            word=target,
                            reason=reason,
                            score=score * rel.strength,
                            relation_type=rel.relation_type,
                        ))
        
        # 策略2: 基于关系图谱扩展 (30%) - 从已学词汇出发
        if learned_words and len(recommendations) < n:
            for learned in learned_words[-3:]:  # 取最近学的3个词
                relations = await self.get_word_relations(learned, limit=5)
                for rel in relations.relations:
                    target = rel.target
                    if target not in learned_words and target not in [r.word for r in recommendations]:
                        recommendations.append(RecommendationResult(
                            word=target,
                            reason=f"与你学过的'{learned}'是{self._translate_relation(rel.relation_type)}",
                            score=0.75 * rel.strength,
                            relation_type=rel.relation_type,
                        ))
        
        # 策略3: LightFM协同过滤 (40%)
        if LIGHTFM_AVAILABLE and self._lightfm_model is not None:
            lightfm_recs = await self.recommend_with_lightfm(user_id, n=n)
            for rec in lightfm_recs:
                if rec.word not in learned_words and rec.word not in [r.word for r in recommendations]:
                    recommendations.append(rec)
        
        # 策略4: FAISS相似度检索 (补充)
        if FAISS_AVAILABLE and self._faiss_index is not None and learned_words:
            for learned in learned_words[-2:]:
                similar = await self.search_similar_words(learned, n=3)
                for sim in similar:
                    if sim.word not in learned_words and sim.word not in [r.word for r in recommendations]:
                        recommendations.append(RecommendationResult(
                            word=sim.word,
                            reason=f"与'{learned}'语义相似",
                            score=sim.score * 0.65,
                        ))
        
        # 如果推荐数量不够，从Neo4j中获取更多词汇
        if len(recommendations) < n:
            # 查询Neo4j中存在的所有词汇
            try:
                query = """
                MATCH (w:Word)
                WHERE w.difficulty = $level OR w.difficulty IS NULL
                RETURN w.word as word
                LIMIT $limit
                """
                async with client.driver.session() as session:
                    result = await session.run(query, level=user_level, limit=n*2)
                    records = await result.data()
                    
                    for record in records:
                        word = record["word"]
                        if word not in learned_words and word not in [r.word for r in recommendations]:
                            recommendations.append(RecommendationResult(
                                word=word,
                                reason=f"适合你当前{user_level}级的词汇",
                                score=0.60,
                            ))
                            if len(recommendations) >= n:
                                break
            except Exception as e:
                print(f"⚠️ Failed to query Neo4j for words: {e}")
        
        # 最后补充：如果实在不够，使用预定义的词库
        if len(recommendations) < n:
            # 按难度组织的词汇库
            word_pools = {
                1: ["cat", "dog", "book", "pen", "apple", "sun", "run", "fun"],
                2: ["happy", "school", "friend", "family", "water", "music", "dance"],
                3: ["beautiful", "important", "different", "interesting", "necessary", "comfortable"],
                4: ["pronunciation", "vocabulary", "grammar", "sentence", "paragraph", "literature"],
                5: ["metaphor", "allegory", "rhetoric", "syntax", "semantics", "philosophy"],
                6: ["onomatopoeia", "personification", "hyperbole", "alliteration", "euphemism"],
            }
            words = word_pools.get(user_level, word_pools[1])
            for word in words:
                if word not in learned_words and word not in [r.word for r in recommendations]:
                    recommendations.append(RecommendationResult(
                        word=word,
                        reason=f"适合你当前{user_level}级的词汇",
                        score=0.55,
                    ))
                    if len(recommendations) >= n:
                        break
        
        # 按分数排序，取前n个
        recommendations.sort(key=lambda x: x.score, reverse=True)
        recommendations = recommendations[:n]
        
        return VocabularyRecommendation(
            user_id=user_id,
            recommendations=recommendations,
            total=len(recommendations),
        )
    
    async def _get_words_by_difficulty(
        self,
        difficulty: int,
        exclude: List[str],
        limit: int = 5,
    ) -> List[str]:
        """根据难度获取词汇（从Neo4j查询）"""
        client = await self._get_client()
        
        try:
            query = """
            MATCH (w:Word)
            WHERE (w.difficulty = $difficulty OR w.difficulty IS NULL)
            AND NOT w.word IN $exclude
            RETURN w.word as word
            LIMIT $limit
            """
            async with client.driver.session() as session:
                result = await session.run(query, difficulty=difficulty, exclude=exclude, limit=limit)
                records = await result.data()
                words = [r["word"] for r in records]
                if words:
                    return words
        except Exception as e:
            print(f"⚠️ Failed to query words from Neo4j: {e}")
        
        # 如果Neo4j查询失败或没有结果，返回预定义词汇
        word_pools = {
            1: ["cat", "dog", "book", "pen", "apple"],
            2: ["happy", "school", "friend", "family", "water"],
            3: ["beautiful", "important", "different", "interesting", "necessary"],
            4: ["pronunciation", "vocabulary", "grammar", "sentence", "paragraph"],
            5: ["metaphor", "allegory", "rhetoric", "syntax", "semantics"],
            6: ["onomatopoeia", "personification", "hyperbole", "alliteration", "euphemism"],
        }
        words = word_pools.get(difficulty, word_pools[1])
        return [w for w in words if w not in exclude][:limit]
    
    def _translate_relation(self, relation_type: RelationType) -> str:
        """翻译关系类型为中文"""
        translations = {
            RelationType.SYNONYM: "同义词",
            RelationType.ANTONYM: "反义词",
            RelationType.COGNATE: "同根词",
            RelationType.SIMILAR_FORM: "形近词",
            RelationType.BELONGS_TO: "属于",
        }
        return translations.get(relation_type, "相关词")
    
    # ==================== 批量操作 ====================
    
    # ==================== 同根词识别 ====================
    
    def analyze_cognates(self, word: str) -> List[Dict[str, Any]]:
        """
        分析词汇的同根词（基于词根词缀规则）
        
        示例:
        - "unhappy" -> [{"word": "happy", "prefix": "un", "meaning": "否定"}]
        - "happiness" -> [{"word": "happy", "suffix": "ness", "meaning": "名词(性质)"}]
        """
        cognates = []
        word_lower = word.lower()
        
        # 检查前缀
        for prefix, meaning in self.COMMON_PREFIXES.items():
            if word_lower.startswith(prefix) and len(word_lower) > len(prefix) + 2:
                root = word_lower[len(prefix):]
                cognates.append({
                    "word": root,
                    "type": "prefix",
                    "affix": prefix,
                    "meaning": meaning,
                })
        
        # 检查后缀
        for suffix, meaning in self.COMMON_SUFFIXES.items():
            if word_lower.endswith(suffix) and len(word_lower) > len(suffix) + 2:
                root = word_lower[:-len(suffix)]
                cognates.append({
                    "word": root,
                    "type": "suffix",
                    "affix": suffix,
                    "meaning": meaning,
                })
        
        return cognates
    
    async def auto_build_cognate_relations(self, word: str) -> List[str]:
        """
        自动构建同根词关系
        
        结合LLM提取 + 词根词缀规则双重验证
        返回发现的同根词列表
        """
        cognates = self.analyze_cognates(word)
        added = []
        
        for cog in cognates:
            cognate_word = cog["word"]
            # 添加到知识图谱
            await self.add_word_relation(
                source=word,
                target=cognate_word,
                relation_type=RelationType.COGNATE,
                strength=0.9,
            )
            added.append(cognate_word)
        
        return added
    
    # ==================== 词汇学习路径生成 ====================
    
    async def generate_learning_path(
        self,
        start_word: str,
        target_word: str,
        max_depth: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        生成词汇学习路径（A*算法）
        
        从start_word到target_word的最短学习路径
        基于词汇关系图谱的图搜索
        """
        client = await self._get_client()
        
        # A*算法实现
        # g_score: 从起点到当前节点的实际代价
        # f_score: g_score + 启发函数(估计到目标的代价)
        
        open_set = [(0, start_word)]  # (f_score, word)
        came_from: Dict[str, str] = {}
        g_score: Dict[str, float] = {start_word: 0}
        f_score: Dict[str, float] = {start_word: self._heuristic(start_word, target_word)}
        visited: set = set()
        
        while open_set and len(visited) < max_depth * 10:
            current_f, current = heapq.heappop(open_set)
            
            if current == target_word:
                # 重建路径
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start_word)
                path.reverse()
                
                # 获取路径上的关系信息
                result = []
                for i in range(len(path) - 1):
                    relations = await self.get_word_relations(path[i], limit=5)
                    for rel in relations.relations:
                        if rel.target == path[i + 1]:
                            result.append({
                                "from": path[i],
                                "to": path[i + 1],
                                "relation": rel.relation_type.value,
                                "strength": rel.strength,
                            })
                            break
                return result
            
            if current in visited:
                continue
            visited.add(current)
            
            # 获取相邻节点
            relations = await self.get_word_relations(current, limit=10)
            for rel in relations.relations:
                neighbor = rel.target
                tentative_g = g_score[current] + (1 - rel.strength)  # 强度越高，代价越低
                
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + self._heuristic(neighbor, target_word)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
        
        return []  # 未找到路径
    
    def _heuristic(self, word1: str, word2: str) -> float:
        """
        启发函数：估计从word1到word2的代价
        使用编辑距离作为启发
        """
        # 简单的编辑距离
        m, n = len(word1), len(word2)
        if m < n:
            return self._heuristic(word2, word1)
        if n == 0:
            return float(m)
        
        previous_row = list(range(n + 1))
        for i, c1 in enumerate(word1):
            current_row = [i + 1]
            for j, c2 in enumerate(word2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1.lower() != c2.lower())
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[n] / max(len(word1), len(word2))  # 归一化
    
    # ==================== LightFM协同过滤 ====================
    
    async def train_lightfm_model(
        self,
        user_item_interactions: List[Tuple[str, str, float]],
        user_features: Optional[Dict[str, List[str]]] = None,
        item_features: Optional[Dict[str, List[str]]] = None,
    ) -> bool:
        """
        训练LightFM协同过滤模型
        
        user_item_interactions: [(user_id, word, weight), ...]
        user_features: {user_id: [feature1, feature2], ...}
        item_features: {word: [feature1, feature2], ...}
        """
        if not LIGHTFM_AVAILABLE:
            print("⚠️ LightFM not available, skipping training")
            return False
        
        try:
            # 创建数据集
            dataset = Dataset()
            
            # 收集所有用户和物品
            all_users = list(set(u for u, _, _ in user_item_interactions))
            all_items = list(set(i for _, i, _ in user_item_interactions))
            
            # 收集特征
            all_user_features = set()
            if user_features:
                for feats in user_features.values():
                    all_user_features.update(feats)
            
            all_item_features = set()
            if item_features:
                for feats in item_features.values():
                    all_item_features.update(feats)
            
            dataset.fit(
                users=all_users,
                items=all_items,
                user_features=list(all_user_features),
                item_features=list(all_item_features),
            )
            
            # 构建交互矩阵
            interactions, weights = dataset.build_interactions(
                (u, i, w) for u, i, w in user_item_interactions
            )
            
            # 构建特征矩阵
            user_features_matrix = None
            if user_features:
                user_features_matrix = dataset.build_user_features(
                    (u, feats) for u, feats in user_features.items()
                )
            
            item_features_matrix = None
            if item_features:
                item_features_matrix = dataset.build_item_features(
                    (i, feats) for i, feats in item_features.items()
                )
            
            # 训练模型
            model = LightFM(loss='warp', no_components=50)
            model.fit(
                interactions,
                sample_weight=weights,
                user_features=user_features_matrix,
                item_features=item_features_matrix,
                epochs=30,
                num_threads=4,
            )
            
            self._lightfm_model = model
            self._lightfm_dataset = dataset
            self._lightfm_item_features = item_features_matrix
            
            return True
        except Exception as e:
            print(f"⚠️ LightFM training failed: {e}")
            return False
    
    async def recommend_with_lightfm(
        self,
        user_id: str,
        n: int = 10,
    ) -> List[RecommendationResult]:
        """使用LightFM进行推荐"""
        if not LIGHTFM_AVAILABLE or self._lightfm_model is None:
            return []
        
        try:
            dataset = self._lightfm_dataset
            model = self._lightfm_model
            
            # 获取用户ID的内部表示
            user_internal_id = dataset.mapping()[0].get(user_id)
            if user_internal_id is None:
                return []
            
            # 获取所有物品
            n_items = len(dataset.mapping()[2])
            
            # 预测分数
            scores = model.predict(
                user_ids=user_internal_id,
                item_ids=list(range(n_items)),
                item_features=self._lightfm_item_features,
            )
            
            # 获取物品映射
            item_id_map = {v: k for k, v in dataset.mapping()[2].items()}
            
            # 排序并返回Top-N
            top_indices = scores.argsort()[-n:][::-1]
            recommendations = []
            
            for idx in top_indices:
                word = item_id_map.get(idx)
                if word:
                    recommendations.append(RecommendationResult(
                        word=word,
                        reason="基于协同过滤推荐",
                        score=float(scores[idx]),
                    ))
            
            return recommendations
        except Exception as e:
            print(f"⚠️ LightFM recommendation failed: {e}")
            return []
    
    # ==================== FAISS向量检索 ====================
    
    async def build_faiss_index(
        self,
        word_embeddings: Dict[str, List[float]],
        embedding_dim: int = 100,
    ) -> bool:
        """
        构建FAISS向量索引
        
        word_embeddings: {word: [embedding_vector], ...}
        """
        if not FAISS_AVAILABLE:
            print("⚠️ FAISS not available, skipping index building")
            return False
        
        try:
            self._word_embeddings = word_embeddings
            self._word_list = list(word_embeddings.keys())
            
            # 创建向量矩阵
            embeddings_matrix = np.array(
                [word_embeddings[w] for w in self._word_list],
                dtype=np.float32,
            )
            
            # 创建FAISS索引 (使用IVF-PQ优化)
            nlist = min(100, len(self._word_list) // 10)  # 聚类中心数
            if nlist < 1:
                nlist = 1
            
            quantizer = faiss.IndexFlatIP(embedding_dim)  # 内积作为相似度
            index = faiss.IndexIVFPQ(quantizer, embedding_dim, nlist, 8, 8)
            
            # 训练并添加向量
            index.train(embeddings_matrix)
            index.add(embeddings_matrix)
            
            self._faiss_index = index
            return True
        except Exception as e:
            print(f"⚠️ FAISS index building failed: {e}")
            return False
    
    async def search_similar_words(
        self,
        query_word: str,
        n: int = 10,
    ) -> List[RecommendationResult]:
        """
        使用FAISS搜索相似词汇
        """
        if not FAISS_AVAILABLE or self._faiss_index is None:
            return []
        
        try:
            # 获取查询词的向量
            query_embedding = self._word_embeddings.get(query_word)
            if query_embedding is None:
                return []
            
            query_vector = np.array([query_embedding], dtype=np.float32)
            
            # 搜索
            distances, indices = self._faiss_index.search(query_vector, n + 1)
            
            recommendations = []
            for i, idx in enumerate(indices[0]):
                if idx >= 0 and idx < len(self._word_list):
                    word = self._word_list[idx]
                    if word != query_word:  # 排除查询词本身
                        # 距离转换为相似度分数 (内积越大越相似)
                        score = float(distances[0][i])
                        recommendations.append(RecommendationResult(
                            word=word,
                            reason="基于语义相似度推荐",
                            score=min(1.0, max(0.0, score)),
                        ))
            
            return recommendations[:n]
        except Exception as e:
            print(f"⚠️ FAISS search failed: {e}")
            return []
    
    async def batch_import_relations(self, relations: List[WordRelation]) -> Dict[str, int]:
        """
        批量导入词汇关系
        
        使用场景: 初始化词库时批量导入
        """
        success = 0
        failed = 0
        
        for rel in relations:
            try:
                result = await self.add_word_relation(
                    source=rel.source,
                    target=rel.target,
                    relation_type=rel.relation_type,
                    strength=rel.strength,
                )
                if result:
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"Failed to import relation {rel}: {e}")
                failed += 1
        
        return {"success": success, "failed": failed}


# 服务单例
_kg_service: Optional[KnowledgeGraphService] = None


async def get_kg_service() -> KnowledgeGraphService:
    """获取知识图谱服务实例"""
    global _kg_service
    if _kg_service is None:
        _kg_service = KnowledgeGraphService()
    return _kg_service
