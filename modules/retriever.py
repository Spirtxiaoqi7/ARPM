import os
import time
import jieba
import math
import numpy as np
from rank_bm25 import BM25Okapi
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
import faiss

class Retriever:
    def __init__(self, vector_db_path: str = "data/vector_db"):
        self.vector_db_path = vector_db_path
        self.bm25 = None
        self.text_chunks = []
        self.chunk_metadata = []
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
        """从磁盘加载数据"""
        import json
        vectors_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "vector_db")
        
        chunks_path = os.path.join(vectors_dir, "chunks.json")
        metadata_path = os.path.join(vectors_dir, "metadata.json")
        faiss_path = os.path.join(vectors_dir, "faiss.index")
        
        try:
            if os.path.exists(chunks_path):
                with open(chunks_path, 'r', encoding='utf-8') as f:
                    self.text_chunks = json.load(f)
                print(f"[OK] Loaded {len(self.text_chunks)} chunks from disk")
            
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    self.chunk_metadata = json.load(f)
            
            # 重建 BM25
            self._build_bm25()
            
            # 加载 FAISS 索引
            if self.encoder and os.path.exists(faiss_path):
                self.index = faiss.read_index(faiss_path)
                print(f"[OK] Loaded FAISS index")
            elif self.encoder:
                self.index = faiss.IndexFlatIP(self.dim)
                
        except Exception as e:
            print(f"[WARNING] Failed to load from disk: {e}")

    def _build_bm25(self):
        """构建 BM25 索引"""
        if self.text_chunks:
            tokenized = [list(jieba.cut(chunk)) for chunk in self.text_chunks]
            self.bm25 = BM25Okapi(tokenized)
        else:
            self.bm25 = None

    def retrieve(self, query: str, current_round: int = 1, k: int = 5) -> List[str]:
        """
        ARPM 混合检索核心：
        1. 向量检索 + BM25 检索
        2. RRF 融合
        3. ARPM 时间戳权重衰减 (exp(-delta/decay))
        """
        if not self.text_chunks:
            return []
            
        # 1. 向量检索
        vector_scores = {}
        if self.encoder and self.index:
            query_vec = self.encoder.encode([query])
            D, I = self.index.search(np.array(query_vec).astype('float32'), k * 2)
            for idx, score in zip(I[0], D[0]):
                if idx != -1:
                    vector_scores[idx] = float(score)
        
        # 2. BM25 检索
        bm25_scores = {}
        if self.bm25:
            tokenized_query = list(jieba.cut(query))
            scores = self.bm25.get_scores(tokenized_query)
            for idx, score in enumerate(scores):
                if score > 0:
                    bm25_scores[idx] = score

        # 3. RRF 融合与时间衰减权重
        DECAY_RATE = float(os.getenv('DECAY_RATE', 20.0))
        PERMANENT_WEIGHT = float(os.getenv('PERMANENT_WEIGHT', 1.0))
        
        all_indices = set(vector_scores.keys()) | set(bm25_scores.keys())
        rrf_scores = {}
        
        max_v = max(vector_scores.values()) if vector_scores else 1
        max_b = max(bm25_scores.values()) if bm25_scores else 1

        for idx in all_indices:
            v_score = vector_scores.get(idx, 0) / max_v
            b_score = bm25_scores.get(idx, 0) / max_b
            base_score = v_score * 0.6 + b_score * 0.4
            
            # ARPM 时间权重
            meta = self.chunk_metadata[idx] if idx < len(self.chunk_metadata) else {}
            timestamp = meta.get("timestamp", time.time())
            permanent = meta.get("permanent", False)
            
            if permanent:
                time_weight = PERMANENT_WEIGHT
            else:
                # 使用真实时间差模拟衰减 (天为单位)
                delta_days = (time.time() - timestamp) / 86400
                time_weight = math.exp(-delta_days / DECAY_RATE)
            
            rrf_scores[idx] = base_score * time_weight
            
        sorted_indices = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:k]
        return [self.text_chunks[idx] for idx, _ in sorted_indices]

    def add_chunks(self, chunks: List[Dict]):
        """批量添加文本块并更新索引"""
        for chunk in chunks:
            text = chunk.get("text", "")
            if text:
                self.text_chunks.append(text)
                self.chunk_metadata.append(chunk.get("metadata", {}))
        
        # 重新构建 BM25
        self._build_bm25()
        
        # 更新向量索引
        if self.encoder and self.index:
            new_texts = [c.get("text", "") for c in chunks if c.get("text", "")]
            embeddings = self.encoder.encode(new_texts)
            self.index.add(np.array(embeddings).astype('float32'))

    def delete_chunk(self, index: int):
        """删除指定索引的文本块"""
        if 0 <= index < len(self.text_chunks):
            self.text_chunks.pop(index)
            self.chunk_metadata.pop(index)
            # 简单起见，删除后重新构建索引
            self._build_bm25()
            if self.encoder and self.index:
                self.index = faiss.IndexFlatIP(self.dim)
                if self.text_chunks:
                    embeddings = self.encoder.encode(self.text_chunks)
                    self.index.add(np.array(embeddings).astype('float32'))
            self.save_to_disk()

    def save_to_disk(self):
        """持久化到磁盘 (参考 DeepseekRAG 格式)"""
        vectors_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "vector_db")
        os.makedirs(vectors_dir, exist_ok=True)
        
        # 保存文本和元数据
        import json
        with open(os.path.join(vectors_dir, "chunks.json"), 'w', encoding='utf-8') as f:
            json.dump(self.text_chunks, f, ensure_ascii=False, indent=2)
        with open(os.path.join(vectors_dir, "metadata.json"), 'w', encoding='utf-8') as f:
            json.dump(self.chunk_metadata, f, ensure_ascii=False, indent=2)
        
        # 保存 FAISS 索引
        if self.index:
            faiss.write_index(self.index, os.path.join(vectors_dir, "faiss.index"))

# 全局单例
retriever = Retriever()
