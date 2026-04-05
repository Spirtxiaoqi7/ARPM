import os
import time
import math
import re
import numpy as np
from typing import List, Dict, Optional, Set, Tuple
from sentence_transformers import SentenceTransformer
import faiss
import jieba

from modules.bm25_plus import BM25PlusScorer


class Retriever:
    def __init__(self, vector_db_path: str = "data/vector_db"):
        self.vector_db_path = vector_db_path
        self.bm25_scorer = None
        
        # 父块数据
        self.parent_chunks = []      # 父块文本（用于生成上下文）
        self.chunk_metadata = []     # 父块元数据
        # 子块数据（用于检索匹配）
        self.child_chunks = []       # 子块文本
        self.child_to_parent = []    # 子块对应的父块索引
        
        # 条件激活：hash -> 条件规则
        self.chunk_conditions = {}   # 存储每个chunk的激活条件
        
        # 场景管理
        self.scenes = []             # 场景列表
        
        self.encoder = None
        self.index = None
        self.dim = 384
        
        # 加载嵌入模型
        model_path = os.getenv("LOCAL_MODEL_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "shibing624", "text2vec-base-chinese"))
        
        if os.path.exists(model_path):
            try:
                self.encoder = SentenceTransformer(model_path)
                self.dim = self.encoder.get_sentence_embedding_dimension()
                print(f"[OK] Loaded model from: {model_path}")
                self.index = faiss.IndexFlatIP(self.dim)
            except Exception as e:
                print(f"[ERROR] Error loading model: {e}")
        else:
            print(f"[WARNING] Model path not found: {model_path}")
        
        # 加载已有数据
        self._load_from_disk()
        
    def _load_from_disk(self):
        """从磁盘加载数据，兼容旧版 chunks.json 格式"""
        import json
        vectors_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "vector_db")
        
        parent_chunks_path = os.path.join(vectors_dir, "parent_chunks.json")
        child_chunks_path = os.path.join(vectors_dir, "child_chunks.json")
        child_map_path = os.path.join(vectors_dir, "child_to_parent.json")
        metadata_path = os.path.join(vectors_dir, "metadata.json")
        faiss_path = os.path.join(vectors_dir, "faiss.index")
        conditions_path = os.path.join(vectors_dir, "chunk_conditions.json")
        scenes_path = os.path.join(vectors_dir, "scenes.json")
        legacy_chunks_path = os.path.join(vectors_dir, "chunks.json")
        
        try:
            # 优先加载新版父子块格式
            if os.path.exists(parent_chunks_path):
                with open(parent_chunks_path, 'r', encoding='utf-8') as f:
                    self.parent_chunks = json.load(f)
                print(f"[OK] Loaded {len(self.parent_chunks)} parent chunks from disk")
                
                if os.path.exists(child_chunks_path):
                    with open(child_chunks_path, 'r', encoding='utf-8') as f:
                        self.child_chunks = json.load(f)
                    print(f"[OK] Loaded {len(self.child_chunks)} child chunks from disk")
                
                if os.path.exists(child_map_path):
                    with open(child_map_path, 'r', encoding='utf-8') as f:
                        self.child_to_parent = json.load(f)
                
                if os.path.exists(metadata_path):
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        self.chunk_metadata = json.load(f)
                
                # 加载条件激活规则
                if os.path.exists(conditions_path):
                    with open(conditions_path, 'r', encoding='utf-8') as f:
                        self.chunk_conditions = json.load(f)
                    print(f"[OK] Loaded {len(self.chunk_conditions)} chunk conditions from disk")
                
                # 加载场景
                if os.path.exists(scenes_path):
                    with open(scenes_path, 'r', encoding='utf-8') as f:
                        self.scenes = json.load(f)
                    print(f"[OK] Loaded {len(self.scenes)} scenes from disk")
            
            # 兼容旧版：若存在旧版 chunks.json 且无新版 parent_chunks，则迁移为父块
            elif os.path.exists(legacy_chunks_path):
                print("[INFO] Migrating legacy chunks.json to parent-child format")
                with open(legacy_chunks_path, 'r', encoding='utf-8') as f:
                    legacy_chunks = json.load(f)
                
                legacy_meta_path = os.path.join(vectors_dir, "metadata.json")
                legacy_metadata = []
                if os.path.exists(legacy_meta_path):
                    with open(legacy_meta_path, 'r', encoding='utf-8') as f:
                        legacy_metadata = json.load(f)
                
                for i, text in enumerate(legacy_chunks):
                    meta = legacy_metadata[i] if i < len(legacy_metadata) else {}
                    # 兼容旧数据中的 Unix 时间戳：若 timestamp 为绝对时间（>1e9），统一视为第 1 轮
                    old_ts = meta.get("timestamp", 1)
                    if isinstance(old_ts, (int, float)) and old_ts > 1e9:
                        meta["timestamp"] = 1
                    # 旧数据无子块信息，将整个文本同时作为父块和子块
                    self.parent_chunks.append(text)
                    self.chunk_metadata.append(meta)
                    self.child_chunks.append(text)
                    self.child_to_parent.append(len(self.parent_chunks) - 1)
                
                print(f"[OK] Migrated {len(self.parent_chunks)} legacy chunks")
                # 迁移后立即保存为新格式
                self.save_to_disk()
            
            # 重建 BM25+（基于子块）
            self._build_bm25_plus()
            
            # 加载 FAISS 索引（基于子块）
            if self.encoder and os.path.exists(faiss_path):
                self.index = faiss.read_index(faiss_path)
                print(f"[OK] Loaded FAISS index")
            elif self.encoder:
                self.index = faiss.IndexFlatIP(self.dim)
                
        except Exception as e:
            print(f"[WARNING] Failed to load from disk: {e}")

    def _build_bm25_plus(self):
        """基于子块构建 BM25+ 索引"""
        if not self.child_chunks:
            self.bm25_scorer = None
            return
        
        # 构建 BM25+ 文档
        documents = []
        for i, chunk_text in enumerate(self.child_chunks):
            # 获取对应的父块元数据
            parent_idx = self.child_to_parent[i] if i < len(self.child_to_parent) else 0
            meta = self.chunk_metadata[parent_idx] if parent_idx < len(self.chunk_metadata) else {}
            
            # 提取标题和标签（如果有）
            title = meta.get('title', '')
            tags = meta.get('tags', [])
            
            documents.append({
                'text': chunk_text,
                'title': title,
                'tags': tags
            })
        
        # 创建 BM25+ 评分器
        self.bm25_scorer = BM25PlusScorer(
            k1=1.5,
            b=0.75,
            delta=0.5,
            field_boosting=True,
            coverage_bonus=True,
            use_stemmer=True,
            remove_stopwords=True
        )
        self.bm25_scorer.index_documents(documents)

    def _apply_temporal_weight(self, score: float, meta: Dict, current_round: int, 
                               decay_rate: float, permanent_weight: float) -> float:
        """
        应用时间权重（支持时间盲标记和怀旧模式）
        
        Args:
            score: 原始得分
            meta: 块元数据
            current_round: 当前对话轮次
            decay_rate: 衰减率
            permanent_weight: 永久记忆权重
        """
        # 检查是否为永久记忆或时间盲标记
        is_permanent = meta.get("permanent", False)
        is_temporally_blind = meta.get("temporally_blind", False)
        
        if is_permanent or is_temporally_blind:
            return score * permanent_weight
        
        # 检查怀旧模式
        nostalgia_enabled = meta.get("nostalgia_enabled", False)
        if nostalgia_enabled:
            nostalgia_factor = meta.get("nostalgia_factor", 0.01)
            timestamp = meta.get("timestamp", 1)
            age = current_round - timestamp
            # 怀旧模式：越久越重要
            boost = 1.0 + (nostalgia_factor * max(0, age))
            return score * min(boost, 3.0)  # 最多3倍提升
        
        # ARPM 标准时间衰减：基于对话轮次差
        timestamp = meta.get("timestamp", 1)
        delta_rounds = abs(current_round - timestamp)
        time_weight = math.exp(-delta_rounds / decay_rate)
        
        return score * time_weight

    def _apply_keyword_boost(self, score: float, meta: Dict, query: str) -> float:
        """
        应用关键词提升
        
        Args:
            score: 原始得分
            meta: 块元数据
            query: 用户查询
        """
        keywords = meta.get("keywords", [])
        if not keywords:
            return score
        
        query_lower = query.lower()
        # 中文分词
        query_tokens = set(jieba.cut(query_lower))
        
        boost_sum = 0.0
        match_count = 0
        
        for kw in keywords:
            if isinstance(kw, dict):
                kw_text = kw.get("text", "").lower()
                kw_weight = kw.get("weight", 1.5)
            else:
                kw_text = str(kw).lower()
                kw_weight = 1.5
            
            # 检查是否匹配（支持部分匹配）
            if kw_text in query_lower or any(kw_text in t for t in query_tokens):
                # 计算贡献（高于1.0的部分）
                contribution = min(kw_weight - 1.0, 0.5)  # 单个关键词最多贡献0.5
                boost_sum += contribution
                match_count += 1
        
        if match_count == 0:
            return score
        
        # 应用衰减缩放（防止滥用）
        # 1个匹配: 30%, 2个匹配: 60%, 3+匹配: 100%
        scaling_factors = {1: 0.3, 2: 0.6}
        scale = scaling_factors.get(min(match_count, 3), 1.0)
        
        final_boost = 1.0 + (boost_sum * scale)
        return score * final_boost

    def _get_scene_for_round(self, round_num: int) -> Optional[Dict]:
        """获取指定轮次所属的场景"""
        for scene in self.scenes:
            if scene.get("start_round", 0) <= round_num <= scene.get("end_round", float('inf')):
                return scene
        return None

    def _apply_scene_aware_decay(self, score: float, meta: Dict, current_round: int,
                                  decay_rate: float) -> float:
        """应用场景感知的时间衰减"""
        # 如果块属于某个场景，使用场景起始时间计算年龄
        scene_id = meta.get("scene_id")
        if scene_id:
            scene = next((s for s in self.scenes if s.get("id") == scene_id), None)
            if scene:
                # 使用场景起始时间
                scene_start = scene.get("start_round", meta.get("timestamp", 1))
                delta = abs(current_round - scene_start)
                return score * math.exp(-delta / decay_rate)
        
        # 检查块是否在查询轮次的场景中
        current_scene = self._get_scene_for_round(current_round)
        if current_scene and meta.get("timestamp"):
            chunk_scene = self._get_scene_for_round(meta["timestamp"])
            if chunk_scene and chunk_scene.get("id") == current_scene.get("id"):
                # 同一场景内，衰减较小
                delta = abs(current_round - meta["timestamp"])
                return score * math.exp(-delta / (decay_rate * 2))  # 衰减减半
        
        return None  # 返回None表示未处理

    def _evaluate_conditions(self, child_idx: int, query: str, 
                             current_round: int = 1) -> bool:
        """
        评估 chunk 的条件激活规则
        
        Args:
            child_idx: 子块索引
            query: 用户查询
            current_round: 当前对话轮次
            
        Returns:
            是否通过条件检查
        """
        parent_idx = self.child_to_parent[child_idx] if child_idx < len(self.child_to_parent) else 0
        meta = self.chunk_metadata[parent_idx] if parent_idx < len(self.chunk_metadata) else {}
        
        conditions = meta.get('conditions')
        if not conditions or not conditions.get('enabled', False):
            return True  # 无条件或条件未启用，默认通过
        
        rules = conditions.get('rules', [])
        if not rules:
            return True
        
        logic = conditions.get('logic', 'AND')
        results = []
        
        for rule in rules:
            rule_type = rule.get('type', 'keyword')
            settings = rule.get('settings', {})
            negate = rule.get('negate', False)
            
            result = False
            
            if rule_type == 'keyword':
                # 关键词匹配
                keywords = settings.get('keywords', [])
                match_mode = settings.get('match_mode', 'any')
                case_sensitive = settings.get('case_sensitive', False)
                
                text_to_check = query
                if not case_sensitive:
                    text_to_check = text_to_check.lower()
                    keywords = [k.lower() for k in keywords]
                
                if match_mode == 'any':
                    result = any(kw in text_to_check for kw in keywords)
                else:  # all
                    result = all(kw in text_to_check for kw in keywords)
            
            elif rule_type == 'regex':
                # 正则表达式匹配
                import re
                patterns = settings.get('patterns', [])
                match_mode = settings.get('match_mode', 'any')
                
                if match_mode == 'any':
                    result = any(re.search(p, query) for p in patterns)
                else:  # all
                    result = all(re.search(p, query) for p in patterns)
            
            elif rule_type == 'round_range':
                # 轮次范围匹配
                min_round = settings.get('min_round', 1)
                max_round = settings.get('max_round', float('inf'))
                result = min_round <= current_round <= max_round
            
            elif rule_type == 'recency':
                # 最近性检查（消息年龄）
                max_age = settings.get('max_messages_ago', 50)
                timestamp = meta.get('timestamp', 1)
                age = current_round - timestamp
                result = age <= max_age
            
            elif rule_type == 'random':
                # 随机概率
                import random
                probability = settings.get('probability', 50)
                result = random.random() * 100 <= probability
            
            # 应用否定
            if negate:
                result = not result
            
            results.append(result)
        
        # 应用逻辑组合
        if logic == 'AND':
            return all(results)
        else:  # OR
            return any(results)

    def retrieve(self, query: str, current_round: int = 1, k: int = 5, 
                 ablation_config: Dict = None) -> List[str]:
        """
        ARPM 混合检索核心（父子块召回）- 增强版：
        1. 在子块上执行向量检索 + BM25+ 检索（可开关）
        2. RRF 融合（可开关BM25+部分）
        3. ARPM 时间戳权重衰减（可开关）
        4. 关键词提升（可开关）
        5. 条件激活过滤
        6. 返回对应父块文本
        
        ablation_config: 消融测试配置
            - arpm_enabled: ARPM总开关（由调用方处理，此方法内假设已开启）
            - bm25_enabled: BM25+检索开关
            - cot_rerank: 思维链重排序开关（由LLM客户端处理）
            - temporal_decay: 时间感知衰减开关
            - keyword_boost: 关键词提升开关
        """
        if not self.child_chunks or not self.parent_chunks:
            return []
        
        # 默认消融测试配置（全部开启）
        if ablation_config is None:
            ablation_config = {
                'bm25_enabled': True,
                'temporal_decay': True,
                'keyword_boost': True
            }
        
        # 配置参数
        DECAY_RATE = float(os.getenv('DECAY_RATE', 20.0))
        PERMANENT_WEIGHT = float(os.getenv('PERMANENT_WEIGHT', 1.0))
        RRF_K = float(os.getenv('RRF_K', 60.0))
        
        # 消融测试：BM25+开关
        bm25_enabled = ablation_config.get('bm25_enabled', True)
        temporal_decay_enabled = ablation_config.get('temporal_decay', True)
        keyword_boost_enabled = ablation_config.get('keyword_boost', True)
        
        # 1. 向量检索（基于子块）- 始终启用
        vector_scores = {}
        if self.encoder and self.index:
            query_vec = self.encoder.encode([query])
            D, I = self.index.search(np.array(query_vec).astype('float32'), min(k * 4, len(self.child_chunks)))
            for idx, score in zip(I[0], D[0]):
                if idx != -1:
                    vector_scores[int(idx)] = float(score)
        
        # 2. BM25+ 检索（基于子块）- 可开关
        bm25_scores = {}
        if bm25_enabled and self.bm25_scorer:
            bm25_results = self.bm25_scorer.search(query, top_k=min(k * 4, len(self.child_chunks)))
            for result in bm25_results:
                bm25_scores[result['index']] = result['score']
        
        # 3. RRF 融合与条件过滤、权重应用
        all_indices = set(vector_scores.keys()) | set(bm25_scores.keys())
        child_rrf_scores = {}
        
        max_v = max(vector_scores.values()) if vector_scores else 1
        max_b = max(bm25_scores.values()) if bm25_scores else 1
        
        for idx in all_indices:
            # 检查条件激活
            if not self._evaluate_conditions(idx, query, current_round):
                continue
            
            # RRF 融合（如果BM25+关闭，则只使用向量检索）
            v_rank = sorted(vector_scores.keys(), key=lambda x: vector_scores[x], reverse=True).index(idx) + 1 if idx in vector_scores else float('inf')
            b_rank = sorted(bm25_scores.keys(), key=lambda x: bm25_scores[x], reverse=True).index(idx) + 1 if idx in bm25_scores else float('inf')
            
            v_score = vector_scores.get(idx, 0) / max_v
            b_score = bm25_scores.get(idx, 0) / max_b if max_b > 0 else 0
            
            # RRF 公式
            rrf_score = 0
            if idx in vector_scores:
                rrf_score += 1 / (RRF_K + v_rank)
            if bm25_enabled and idx in bm25_scores:
                rrf_score += 1 / (RRF_K + b_rank)
            
            # 加权基础得分
            if bm25_enabled:
                base_score = v_score * 0.6 + b_score * 0.4
            else:
                base_score = v_score  # BM25关闭时只使用向量得分
            
            # 获取父块元数据
            parent_idx = self.child_to_parent[idx] if idx < len(self.child_to_parent) else 0
            meta = self.chunk_metadata[parent_idx] if parent_idx < len(self.chunk_metadata) else {}
            
            # 消融测试：时间感知衰减开关
            if temporal_decay_enabled:
                # 应用场景感知衰减（如果适用）
                scene_score = self._apply_scene_aware_decay(base_score, meta, current_round, DECAY_RATE)
                if scene_score is not None:
                    final_score = scene_score
                else:
                    # 应用标准时间权重
                    final_score = self._apply_temporal_weight(base_score, meta, current_round, DECAY_RATE, PERMANENT_WEIGHT)
            else:
                final_score = base_score
            
            # 消融测试：关键词提升开关
            if keyword_boost_enabled:
                final_score = self._apply_keyword_boost(final_score, meta, query)
            
            # 结合 RRF 和加权得分
            combined_score = rrf_score * 0.5 + final_score * 0.5
            child_rrf_scores[idx] = combined_score
        
        # 4. 子块映射到父块，合并得分，返回父块
        parent_scores = {}
        for child_idx, score in child_rrf_scores.items():
            parent_idx = self.child_to_parent[child_idx]
            if parent_idx not in parent_scores or parent_scores[parent_idx] < score:
                parent_scores[parent_idx] = score
        
        sorted_parents = sorted(parent_scores.items(), key=lambda x: x[1], reverse=True)[:k]
        return [self.parent_chunks[idx] for idx, _ in sorted_parents]

    def add_chunks(self, chunks: List[Dict]):
        """批量添加文本块并更新索引"""
        new_child_chunks = []
        new_child_to_parent = []
        
        for chunk in chunks:
            text = chunk.get("text", "")
            meta = chunk.get("metadata", {})
            if not text:
                continue
            
            parent_idx = len(self.parent_chunks)
            self.parent_chunks.append(text)
            self.chunk_metadata.append(meta)
            
            # 提取子块
            children = meta.get("children", [text])
            for child_text in children:
                if child_text:
                    new_child_chunks.append(child_text)
                    new_child_to_parent.append(parent_idx)
        
        self.child_chunks.extend(new_child_chunks)
        self.child_to_parent.extend(new_child_to_parent)
        
        # 重新构建 BM25+
        self._build_bm25_plus()
        
        # 更新向量索引（基于子块）
        if self.encoder and self.index and new_child_chunks:
            embeddings = self.encoder.encode(new_child_chunks)
            self.index.add(np.array(embeddings).astype('float32'))

    def delete_chunk(self, index: int):
        """删除指定索引的父块文本块"""
        if 0 <= index < len(self.parent_chunks):
            self.parent_chunks.pop(index)
            self.chunk_metadata.pop(index)
            # 重建子块与映射（因为父块索引变化了）
            # 简单起见，删除后重新构建所有索引
            old_chunks = []
            for p_idx, (p_text, meta) in enumerate(zip(self.parent_chunks, self.chunk_metadata)):
                old_chunks.append({
                    "text": p_text,
                    "metadata": meta
                })
            
            self.parent_chunks = []
            self.chunk_metadata = []
            self.child_chunks = []
            self.child_to_parent = []
            self._build_bm25_plus()
            if self.encoder:
                self.index = faiss.IndexFlatIP(self.dim)
            
            self.add_chunks(old_chunks)
            self.save_to_disk()

    # ==================== 时间盲标记 ====================
    def set_chunk_temporally_blind(self, parent_idx: int, blind: bool = True):
        """
        设置/取消时间盲标记
        
        Args:
            parent_idx: 父块索引
            blind: True 设置为时间盲，False 取消
        """
        if 0 <= parent_idx < len(self.chunk_metadata):
            self.chunk_metadata[parent_idx]['temporally_blind'] = blind
            self.save_to_disk()
            print(f"[OK] Set chunk {parent_idx} temporally_blind={blind}")

    # ==================== 条件激活 ====================
    def set_chunk_conditions(self, parent_idx: int, conditions: Dict):
        """
        设置 chunk 的条件激活规则
        """
        if 0 <= parent_idx < len(self.chunk_metadata):
            self.chunk_metadata[parent_idx]['conditions'] = conditions
            self.save_to_disk()
            print(f"[OK] Set conditions for chunk {parent_idx}")

    # ==================== 关键词提升 ====================
    def set_chunk_keywords(self, parent_idx: int, keywords: List[Dict]):
        """
        设置 chunk 的关键词列表
        
        Args:
            parent_idx: 父块索引
            keywords: 关键词列表，格式 [{"text": "关键词", "weight": 2.0}, ...]
        """
        if 0 <= parent_idx < len(self.chunk_metadata):
            self.chunk_metadata[parent_idx]['keywords'] = keywords
            self.save_to_disk()
            print(f"[OK] Set {len(keywords)} keywords for chunk {parent_idx}")

    # ==================== 怀旧模式 ====================
    def set_chunk_nostalgia(self, parent_idx: int, enabled: bool = True, factor: float = 0.01):
        """
        设置 chunk 的怀旧模式
        
        Args:
            parent_idx: 父块索引
            enabled: 是否启用怀旧模式
            factor: 怀旧因子（每轮提升比例，默认0.01=1%）
        """
        if 0 <= parent_idx < len(self.chunk_metadata):
            self.chunk_metadata[parent_idx]['nostalgia_enabled'] = enabled
            self.chunk_metadata[parent_idx]['nostalgia_factor'] = factor
            self.save_to_disk()
            print(f"[OK] Set chunk {parent_idx} nostalgia={enabled}, factor={factor}")

    # ==================== 场景管理 ====================
    def create_scene(self, start_round: int, end_round: int, title: str = "", 
                     summary: str = "", keywords: List[str] = None) -> str:
        """
        创建场景
        
        Args:
            start_round: 场景起始轮次
            end_round: 场景结束轮次
            title: 场景标题
            summary: 场景摘要
            keywords: 场景关键词
            
        Returns:
            场景ID
        """
        import uuid
        scene_id = str(uuid.uuid4())[:8]
        
        scene = {
            "id": scene_id,
            "start_round": start_round,
            "end_round": end_round,
            "title": title or f"场景 {start_round}-{end_round}",
            "summary": summary,
            "keywords": keywords or [],
            "created_at": time.time()
        }
        
        self.scenes.append(scene)
        
        # 标记该场景范围内的 chunk
        for i, meta in enumerate(self.chunk_metadata):
            ts = meta.get("timestamp", 1)
            if start_round <= ts <= end_round:
                meta["scene_id"] = scene_id
        
        self.save_to_disk()
        print(f"[OK] Created scene {scene_id}: rounds {start_round}-{end_round}")
        return scene_id

    def delete_scene(self, scene_id: str):
        """删除场景"""
        self.scenes = [s for s in self.scenes if s.get("id") != scene_id]
        
        # 清除 chunk 的场景标记
        for meta in self.chunk_metadata:
            if meta.get("scene_id") == scene_id:
                meta.pop("scene_id", None)
        
        self.save_to_disk()
        print(f"[OK] Deleted scene {scene_id}")

    def get_scenes(self) -> List[Dict]:
        """获取所有场景"""
        return self.scenes

    @property
    def text_chunks(self):
        """兼容旧接口：返回父块文本列表"""
        return self.parent_chunks

    def get_chunk_info(self, parent_idx: int) -> Dict:
        """获取 chunk 的详细信息"""
        if 0 <= parent_idx < len(self.parent_chunks):
            meta = self.chunk_metadata[parent_idx]
            return {
                'index': parent_idx,
                'text': self.parent_chunks[parent_idx][:200] + '...' if len(self.parent_chunks[parent_idx]) > 200 else self.parent_chunks[parent_idx],
                'metadata': meta,
                'child_count': sum(1 for p in self.child_to_parent if p == parent_idx),
                'in_scene': meta.get('scene_id') is not None
            }
        return {}

    def save_to_disk(self):
        """持久化到磁盘"""
        vectors_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "vector_db")
        os.makedirs(vectors_dir, exist_ok=True)
        
        import json
        with open(os.path.join(vectors_dir, "parent_chunks.json"), 'w', encoding='utf-8') as f:
            json.dump(self.parent_chunks, f, ensure_ascii=False, indent=2)
        with open(os.path.join(vectors_dir, "child_chunks.json"), 'w', encoding='utf-8') as f:
            json.dump(self.child_chunks, f, ensure_ascii=False, indent=2)
        with open(os.path.join(vectors_dir, "child_to_parent.json"), 'w', encoding='utf-8') as f:
            json.dump(self.child_to_parent, f, ensure_ascii=False, indent=2)
        with open(os.path.join(vectors_dir, "metadata.json"), 'w', encoding='utf-8') as f:
            json.dump(self.chunk_metadata, f, ensure_ascii=False, indent=2)
        with open(os.path.join(vectors_dir, "scenes.json"), 'w', encoding='utf-8') as f:
            json.dump(self.scenes, f, ensure_ascii=False, indent=2)
        
        # 保存 FAISS 索引
        if self.index:
            faiss.write_index(self.index, os.path.join(vectors_dir, "faiss.index"))


# 全局单例
retriever = Retriever()
