"""
检索器 - 双层决策 + 双源召回 (知识库 + 对话历史)
"""
from typing import List, Dict, Optional

from storage.vector_store import vector_store
from utils.bm25_plus import BM25PlusScorer
from config import RetrievalConfig

class Retriever:
    """双源检索器"""
    
    def __init__(self):
        self.config = RetrievalConfig()
        # BM25+ 用于知识库的关键词检索
        self.bm25_scorer: Optional[BM25PlusScorer] = None
        self._build_bm25_index()
    
    def _build_bm25_index(self):
        """构建BM25索引（基于知识库父块）"""
        knowledge_chunks = vector_store.knowledge_chunks
        self.bm25_scorer = None
        if not knowledge_chunks:
            return
        
        documents = [c["text"] for c in knowledge_chunks]
        self.bm25_scorer = BM25PlusScorer()
        self.bm25_scorer.index_documents(documents)
        print(f"[OK] BM25 index built: {len(documents)} documents")
    
    def retrieve(
        self,
        query: str,
        session_id: Optional[str] = None,
        current_round: int = 1,
        current_scene_id: Optional[str] = None,  # [接口保留] 暂不启用
        ablation_config: Optional[Dict] = None,
        user_name: Optional[str] = None,
        character_name: Optional[str] = None,
        similarity_threshold: Optional[float] = None,
        tuning_config: Optional[Dict] = None
    ) -> Dict:
        """
        双源检索主入口（支持消融实验开关 + 角色感知检索）
        
        Args:
            query: 用户查询
            session_id: 会话ID
            current_round: 当前轮次
            current_scene_id: 当前场景ID (接口保留，暂不启用)
            ablation_config: 消融实验配置
            user_name: 用户名称（用于角色感知检索）
            character_name: 助手/角色名称（用于角色感知检索）
            similarity_threshold: 相似度阈值(0-1)，低于此值的结果会被过滤，默认0.5
        
        Returns:
            {
                "knowledge": [...],      # 知识库结果
                "chat_history": [...],   # 对话历史结果
                "total_knowledge": int,  # 知识库数量
                "total_chat": int,       # 对话历史数量
                "rag_enabled": bool,     # RAG是否启用
                "kb_enabled": bool,      # 知识库是否启用
                "chat_enabled": bool     # 对话历史是否启用
            }
        
        Note:
            [暂不启用] current_scene_id 参数接口已保留，但场景隔离功能暂不生效。
            如需启用，需完善 scene_id 的数据存储链路。
        """
        ablation = ablation_config or {}
        
        # 主开关：RAG整体开关
        rag_enabled = ablation.get("rag_enabled", True)
        if not rag_enabled:
            # RAG完全关闭，返回空结果（纯LLM模式）
            return {
                "knowledge": [],
                "chat_history": [],
                "total_knowledge": 0,
                "total_chat": 0,
                "rag_enabled": False,
                "kb_enabled": False,
                "chat_enabled": False,
                "note": "RAG已关闭，使用纯LLM模式"
            }
        
        # 子开关：双源召回独立控制
        kb_enabled = ablation.get("kb_enabled", True)
        chat_enabled = ablation.get("chat_enabled", True)
        bm25_enabled = ablation.get("bm25_enabled", True)
        tuning = tuning_config or {}
        knowledge_k = max(1, int(tuning.get("knowledge_k", self.config.KNOWLEDGE_K)))
        chat_history_k = max(1, int(tuning.get("chat_history_k", self.config.CHAT_HISTORY_K)))
        
        # 相似度阈值（前端传入或取配置默认值）
        threshold = similarity_threshold if similarity_threshold is not None else tuning.get("similarity_threshold", self.config.SIMILARITY_THRESHOLD)
        
        # 知识库召回 (k=5)
        knowledge_results = []
        if kb_enabled:
            knowledge_results = self._retrieve_knowledge(
                query, 
                k=knowledge_k,
                use_bm25=bm25_enabled,
                user_name=user_name,
                character_name=character_name,
                tuning_config=tuning
            )
        
        # 对话历史召回 (k=10)
        chat_results = []
        if chat_enabled:
            chat_results = self._retrieve_chat_history(
                query,
                session_id=session_id,
                k=chat_history_k,
                user_name=user_name,
                character_name=character_name,
                tuning_config=tuning
            )
        
        # 应用相似度阈值过滤（如果threshold=0则不过滤）
        print(f"[Retrieve] Applying threshold {threshold}, knowledge: {len(knowledge_results)}, chat: {len(chat_results)}")
        if threshold > 0:
            knowledge_before = len(knowledge_results)
            chat_before = len(chat_results)
            knowledge_results = [r for r in knowledge_results if r.get("score", 0) >= threshold]
            chat_results = [r for r in chat_results if r.get("score", 0) >= threshold]
            print(f"[Retrieve] After filtering: knowledge {knowledge_before}->{len(knowledge_results)}, chat {chat_before}->{len(chat_results)}")
            # 打印被过滤掉的结果分数
            if knowledge_before > len(knowledge_results):
                print(f"[Retrieve] Knowledge scores filtered: {[r.get('score', 0) for r in knowledge_results[:3]]}")
        
        return {
            "knowledge": knowledge_results,
            "chat_history": chat_results,
            "total_knowledge": len(knowledge_results),
            "total_chat": len(chat_results),
            "rag_enabled": True,
            "kb_enabled": kb_enabled,
            "chat_enabled": chat_enabled,
            "similarity_threshold": threshold
        }
    
    def _retrieve_knowledge(
        self,
        query: str,
        k: int = 5,
        use_bm25: bool = True,
        user_name: Optional[str] = None,
        character_name: Optional[str] = None,
        tuning_config: Optional[Dict] = None
    ) -> List[Dict]:
        """
        知识库检索 - 向量 + BM25融合 + 角色感知增强（查询阶段融入）
        
        策略:
        1. 构建角色感知增强查询：将用户/助手名称打包进查询
        2. 使用增强查询进行向量+BM25检索
        3. 对召回结果中包含角色名称的给予额外加权
        
        鲁棒处理：
        - 即使历史记录为空（如第一次打招呼），增强查询也能帮助定位角色相关文本
        - 向量检索和BM25双重保障，避免单一检索方式失效
        """
        # 步骤1：构建角色感知增强查询
        # 将用户和助手名称作为查询前缀，让它们在向量编码中发挥作用
        enhanced_query = self._build_role_aware_query(query, user_name, character_name, tuning_config=tuning_config)
        
        results = []
        
        # 步骤2：使用增强查询进行检索（向量 + BM25）
        # 向量检索：语义匹配增强查询（包含角色名称）
        vector_results = vector_store.search_knowledge(enhanced_query, k=k * 2)
        
        # BM25检索：关键词匹配增强查询
        bm25_results = []
        if use_bm25 and self.bm25_scorer:
            bm25_raw = self.bm25_scorer.search(enhanced_query, top_k=k * 2)
            # 映射到父块
            for r in bm25_raw:
                idx = r["index"]
                if idx < len(vector_store.knowledge_chunks):
                    chunk = vector_store.knowledge_chunks[idx]
                    bm25_results.append({
                        **chunk,
                        "score": r["score"]
                    })
        
        # RRF融合向量+BM25结果
        if use_bm25 and bm25_results:
            rrf_k = int((tuning_config or {}).get("rrf_k", self.config.RRF_K))
            results = self._rrf_fusion(vector_results, bm25_results, k=rrf_k, top_k=k * 2)
            # RRF分数太小(0.01-0.03)，需要归一化到0-1范围以匹配向量相似度
            if results:
                max_score = max(r.get("score", 0) for r in results)
                if max_score > 0:
                    for r in results:
                        r["score"] = r["score"] / max_score  # 归一化到0-1
        else:
            results = vector_results[:k * 2]
        
        # 步骤3：后处理加权（鲁棒性增强）
        # 即使增强查询召回了结果，进一步对明确包含角色名称的片段加权
        if user_name or character_name:
            results = self._apply_kb_role_weighting(
                results,
                user_name,
                character_name,
                tuning_config=tuning_config
            )
        
        return results[:k]
    
    def _apply_kb_role_weighting(
        self,
        results: List[Dict],
        user_name: Optional[str],
        character_name: Optional[str],
        tuning_config: Optional[Dict] = None
    ) -> List[Dict]:
        """
        应用知识库角色感知权重
        
        加权策略:
        - 知识库文本包含用户名称: +0.08
        - 知识库文本包含助手名称: +0.08
        - 知识库来源包含角色相关: +0.05
        
        说明：知识库的角色权重较低，因为知识库通常是背景设定文档，
        不像对话历史那样直接与当前角色绑定。两个名称都出现最多+0.21。
        """
        weighted_results = []
        tuning = tuning_config or {}
        kb_user_boost = float(tuning.get("kb_user_name_boost", 0.08))
        kb_character_boost = float(tuning.get("kb_character_name_boost", 0.08))
        kb_source_boost = float(tuning.get("kb_source_name_boost", 0.05))
        
        # 先计算所有加权后的分数用于后续归一化
        temp_scores = []
        for result in results:
            score_boost = 0.0
            text = result.get("text", "")
            source = result.get("source", "")
            
            # 用户名称出现在知识库文本中（降低权重，更注重语义）
            if user_name and user_name in text:
                score_boost += kb_user_boost
            
            # 助手名称出现在知识库文本中（降低权重，更注重语义）
            if character_name and character_name in text:
                score_boost += kb_character_boost
            
            # 来源文件名包含角色相关关键词（如角色设定文档）
            if character_name and character_name in source:
                score_boost += kb_source_boost
            
            original_score = result.get("score", 1.0)
            final_score = original_score + score_boost
            temp_scores.append((result, final_score, score_boost))
        
        # 归一化分数到0-1范围
        if temp_scores:
            max_score = max(s[1] for s in temp_scores)
            if max_score > 0:
                for result, score, boost in temp_scores:
                    result["score"] = score / max_score
                    result["kb_role_weight_boost"] = boost
                    weighted_results.append(result)
        
        # 按加权分数重新排序
        weighted_results.sort(key=lambda x: x["score"], reverse=True)
        return weighted_results
    
    def _retrieve_chat_history(
        self,
        query: str,
        session_id: Optional[str] = None,
        k: int = 10,
        user_name: Optional[str] = None,
        character_name: Optional[str] = None,
        tuning_config: Optional[Dict] = None
    ) -> List[Dict]:
        """
        对话历史检索 - 角色感知增强检索
        
        策略:
        1. 使用原始查询 + 角色名称上下文进行检索
        2. 对包含用户/助手名称的结果进行加权
        3. 同会话的结果优先
        """
        # 构建增强查询：将用户和助手名称融入查询
        enhanced_query = self._build_role_aware_query(query, user_name, character_name, tuning_config=tuning_config)
        
        # 使用增强查询进行向量检索
        results = vector_store.search_chat_history(
            enhanced_query, 
            session_id=session_id, 
            k=k * 2  # 多检索一些用于重排序
        )
        
        # 角色感知重排序：对与当前角色相关的记录加权
        if user_name or character_name:
            results = self._apply_role_weighting(
                results, 
                query, 
                user_name, 
                character_name,
                session_id,
                tuning_config=tuning_config
            )
        
        return results[:k]
    
    def _build_role_aware_query(
        self, 
        query: str, 
        user_name: Optional[str], 
        character_name: Optional[str],
        tuning_config: Optional[Dict] = None
    ) -> str:
        """
        构建角色感知查询
        
        将用户和助手名称作为上下文融入查询，提高检索相关性
        """
        tuning = tuning_config or {}
        if not tuning.get("role_query_prefix_enabled", True):
            return query

        context_parts = []
        
        if user_name:
            context_parts.append(f"用户{user_name}")
        if character_name:
            context_parts.append(f"助手{character_name}")
        
        if context_parts:
            # 将角色上下文融入查询，但保持原始查询的主导地位
            # 格式: "[用户小明][助手小红] 原始查询"
            context_str = "".join(f"[{p}]" for p in context_parts)
            return f"{context_str} {query}"
        
        return query
    
    def _apply_role_weighting(
        self,
        results: List[Dict],
        original_query: str,
        user_name: Optional[str],
        character_name: Optional[str],
        current_session_id: Optional[str],
        tuning_config: Optional[Dict] = None
    ) -> List[Dict]:
        """
        应用角色感知权重（已降低，更注重语义内容）
        
        加权策略:
        - 同会话: +0.15
        - 包含用户名称: +0.1（完全匹配）/+0.04（文本包含）
        - 包含助手名称: +0.1（完全匹配）/+0.04（文本包含）
        - 两个名称都出现约 +0.3 左右，不过度干扰语义排序
        """
        weighted_results = []
        tuning = tuning_config or {}
        same_session_boost = float(tuning.get("chat_same_session_boost", 0.15))
        exact_name_boost = float(tuning.get("chat_exact_name_boost", 0.10))
        text_name_boost = float(tuning.get("chat_text_name_boost", 0.04))
        
        for result in results:
            score_boost = 0.0
            text = result.get("text", "")
            result_user = result.get("user_name", "")
            result_char = result.get("character_name", "")
            result_session = result.get("session_id", "")
            
            # 同会话加权（降低权重，避免过度干扰语义）
            if current_session_id and result_session == current_session_id:
                score_boost += same_session_boost
            
            # 用户名匹配加权（降低，更注重内容语义）
            if user_name and result_user == user_name:
                score_boost += exact_name_boost
            elif user_name and user_name in text:
                score_boost += text_name_boost
            
            # 助手名匹配加权（降低，更注重内容语义）
            if character_name and result_char == character_name:
                score_boost += exact_name_boost
            elif character_name and character_name in text:
                score_boost += text_name_boost
            
            # 应用权重
            semantic_score = result.get("semantic_score", result.get("score", 1.0))
            result["semantic_score"] = semantic_score
            result["score"] = semantic_score + score_boost
            result["role_weight_boost"] = score_boost  # 记录权重信息
            
            weighted_results.append(result)
        
        # 按加权分数重新排序
        weighted_results.sort(key=lambda x: x["score"], reverse=True)
        return weighted_results
    
    def _rrf_fusion(
        self,
        vector_results: List[Dict],
        bm25_results: List[Dict],
        k: int = 60,
        top_k: int = 5
    ) -> List[Dict]:
        """
        RRF (Reciprocal Rank Fusion) 融合
        并将RRF分数归一化到0-1范围，与向量相似度对齐
        """
        scores = {}
        
        # 向量得分
        for rank, result in enumerate(vector_results):
            chunk_id = result.get("chunk_id")
            if chunk_id:
                scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank + 1)
        
        # BM25得分
        for rank, result in enumerate(bm25_results):
            chunk_id = result.get("chunk_id")
            if chunk_id:
                scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank + 1)
        
        # 获取完整chunk信息
        chunk_map = {c["chunk_id"]: c for c in vector_store.knowledge_chunks}
        
        # 排序
        sorted_results = []
        for chunk_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]:
            if chunk_id in chunk_map:
                chunk = chunk_map[chunk_id].copy()
                chunk["score"] = score
                sorted_results.append(chunk)
        
        return sorted_results
    
    def add_knowledge(self, chunks: List[Dict]) -> List[str]:
        """
        添加知识库文档
        """
        chunk_ids = vector_store.add_knowledge_chunks(chunks)
        # 重建BM25索引
        self._build_bm25_index()
        return chunk_ids
    
    def add_chat_atom(self, chunk: Dict) -> str:
        """
        实时添加对话原子块
        """
        return vector_store.add_chat_atom(chunk, session_id=chunk.get("session_id"))
    
    def get_stats(self) -> Dict:
        """获取检索统计"""
        return {
            "knowledge": vector_store.get_knowledge_stats(),
            "chat": vector_store.get_chat_stats(),
            "bm25_ready": self.bm25_scorer is not None
        }

# 全局实例
retriever = Retriever()
