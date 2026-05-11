"""
双索引向量存储系统 - 多会话隔离版本
- knowledge索引: 全局共享（所有会话共享知识库）
- chat索引: 按session隔离（每个会话独立存储）

存储结构:
  vector_db/
    knowledge/
      metadata.json      # 全局知识库元数据
      faiss.index        # 全局知识库索引
    chat/
      {session_id}/
        metadata.json    # 该会话的对话元数据
        faiss.index      # 该会话的对话索引
"""
import os
import json
import uuid
import tempfile
import numpy as np
from typing import List, Dict, Optional, Tuple
from sentence_transformers import SentenceTransformer
import faiss
import shutil

from config import VECTOR_DB_PATH, MODEL_PATH
from storage.schema import TextChunk


def _is_ascii_path(path: str) -> bool:
    try:
        os.fspath(path).encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def _faiss_read_index(index_path: str):
    """Read FAISS index through an ASCII temp path when the project path is non-ASCII."""
    if _is_ascii_path(index_path):
        return faiss.read_index(index_path)

    tmp_path = os.path.join(tempfile.gettempdir(), f"arpm_faiss_{uuid.uuid4().hex}.index")
    try:
        shutil.copyfile(index_path, tmp_path)
        return faiss.read_index(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _faiss_write_index(index, index_path: str):
    """Write FAISS index through an ASCII temp path when the project path is non-ASCII."""
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    if _is_ascii_path(index_path):
        faiss.write_index(index, index_path)
        return

    tmp_path = os.path.join(tempfile.gettempdir(), f"arpm_faiss_{uuid.uuid4().hex}.index")
    try:
        faiss.write_index(index, tmp_path)
        shutil.copyfile(tmp_path, index_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


class DualVectorStore:
    """双索引向量存储 - 支持多会话隔离"""
    
    def __init__(self):
        self.knowledge_dir = os.path.join(VECTOR_DB_PATH, "knowledge")
        self.chat_dir = os.path.join(VECTOR_DB_PATH, "chat")
        os.makedirs(self.knowledge_dir, exist_ok=True)
        os.makedirs(self.chat_dir, exist_ok=True)
        
        # 加载模型
        self.encoder = None
        self.dim = 384
        self._load_model()
        
        # 知识库 - 全局共享
        self.knowledge_index = None
        self.knowledge_chunks: List[Dict] = []
        
        # 对话历史 - 按session隔离 (懒加载)
        # chat_indices[session_id] = faiss.Index
        # chat_chunks[session_id] = List[Dict]
        self._chat_indices: Dict[str, faiss.Index] = {}
        self._chat_chunks: Dict[str, List[Dict]] = {}
        self._loaded_sessions: set = set()  # 已加载的session缓存
        
        # 加载知识库
        self._load_knowledge_store()
        
        # 迁移旧数据（从单一文件到多会话隔离）
        self._migrate_old_chat_data()
    
    def _load_model(self):
        """加载编码模型"""
        model_path = str(MODEL_PATH)
        if os.path.exists(model_path):
            try:
                self.encoder = SentenceTransformer(model_path)
                self.dim = self.encoder.get_sentence_embedding_dimension()
                print(f"[OK] Loaded model: {model_path}, dim={self.dim}")
            except Exception as e:
                print(f"[ERROR] Failed to load model: {e}")
        else:
            print(f"[WARNING] Model not found: {model_path}")

    def _encode_texts(self, texts, normalize: bool = False):
        """Encode texts with optional embedding normalization."""
        return self.encoder.encode(
            texts,
            normalize_embeddings=normalize
        )

    def _compute_normalized_similarities(self, query: str, texts: List[str]) -> List[float]:
        """Return bounded cosine similarities in [0, 1]."""
        if not self.encoder or not texts:
            return []

        query_vec = self._encode_texts([query], normalize=True)[0]
        text_vecs = self._encode_texts(texts, normalize=True)
        scores = np.dot(np.asarray(text_vecs, dtype='float32'), np.asarray(query_vec, dtype='float32'))
        return [max(0.0, min(1.0, float(score))) for score in scores]
    
    # ==================== 知识库索引操作（全局共享）====================
    
    def add_knowledge_chunks(self, chunks: List[Dict]) -> List[str]:
        """添加知识库父块（全局共享）"""
        if not self.encoder:
            raise RuntimeError("Encoder not loaded")
        
        chunk_ids = []
        embeddings = []
        
        for chunk in chunks:
            chunk_id = str(uuid.uuid4())[:8]
            chunk_ids.append(chunk_id)
            
            parent_meta = {
                "chunk_id": chunk_id,
                "text": chunk["text"],
                "children": chunk.get("children", [chunk["text"]]),
                "timestamp": chunk.get("metadata", {}).get("timestamp", {"round_num": 1, "physical_time": ""}),
                "source": chunk.get("metadata", {}).get("source", "upload"),
                "source_type": "knowledge"
            }
            self.knowledge_chunks.append(parent_meta)
            parent_idx = len(self.knowledge_chunks) - 1
            
            for child_text in parent_meta["children"]:
                embedding = self._encode_texts([child_text])
                embeddings.append(embedding[0])
                self.knowledge_chunks[parent_idx].setdefault("child_mappings", []).append(
                    len(embeddings) - 1
                )
        
        if embeddings:
            embeddings = np.array(embeddings).astype('float32')
            if self.knowledge_index is None:
                self.knowledge_index = faiss.IndexFlatIP(self.dim)
            self.knowledge_index.add(embeddings)
        
        self._save_knowledge_store()
        return chunk_ids
    
    def search_knowledge(self, query: str, k: int = 5) -> List[Dict]:
        """检索知识库（全局共享）"""
        print(f"[Knowledge] Searching for: '{query[:50]}...' (k={k})")
        print(f"[Knowledge] Encoder loaded: {self.encoder is not None}, Index: {self.knowledge_index is not None}")
        
        if not self.encoder:
            print(f"[Knowledge] ERROR: Encoder not loaded")
            return []
        
        if self.knowledge_index is None:
            print(f"[Knowledge] ERROR: Knowledge index is None")
            return []
        
        if self.knowledge_index.ntotal == 0:
            print(f"[Knowledge] ERROR: Knowledge index is empty (0 vectors)")
            return []
        
        query_vec = self._encode_texts([query])
        search_k = min(k * 3, self.knowledge_index.ntotal)
        D, I = self.knowledge_index.search(np.array(query_vec).astype('float32'), search_k)
        
        print(f"[Knowledge] Raw search returned {len(I[0])} results")
        
        parent_scores = {}
        for idx, score in zip(I[0], D[0]):
            if idx == -1:
                continue
            for p_idx, chunk in enumerate(self.knowledge_chunks):
                mappings = chunk.get("child_mappings", [])
                if idx in mappings:
                    if p_idx not in parent_scores or parent_scores[p_idx]["score"] < score:
                        parent_scores[p_idx] = {"chunk": chunk, "score": float(score)}
                    break
        
        sorted_parents = sorted(parent_scores.items(), key=lambda x: x[1]["score"], reverse=True)[:k]
        print(f"[Knowledge] Returning {len(sorted_parents)} parent chunks")

        results = []
        for _, item in sorted_parents:
            chunk = item["chunk"].copy()
            chunk["score"] = item["score"]
            results.append(chunk)
        return results
    
    # ==================== 对话索引操作（按session隔离）====================
    
    def _ensure_session_loaded(self, session_id: str):
        """确保指定session的索引已加载"""
        if session_id in self._loaded_sessions:
            return
        
        session_dir = os.path.join(self.chat_dir, session_id)
        meta_path = os.path.join(session_dir, "metadata.json")
        index_path = os.path.join(session_dir, "faiss.index")
        
        # 加载元数据
        if os.path.exists(meta_path):
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    self._chat_chunks[session_id] = json.load(f)
                print(f"[OK] Loaded chat metadata for session {session_id}: {len(self._chat_chunks[session_id])} chunks")
            except Exception as e:
                print(f"[ERROR] Failed to load chat metadata for {session_id}: {e}")
                self._chat_chunks[session_id] = []
        else:
            self._chat_chunks[session_id] = []
            print(f"[INFO] No chat metadata found for session {session_id}, creating new")
        
        # 加载或创建索引
        if self.encoder:
            if os.path.exists(index_path):
                try:
                    self._chat_indices[session_id] = _faiss_read_index(index_path)
                    print(f"[OK] Loaded chat index for session {session_id}: {self._chat_indices[session_id].ntotal} vectors")
                except Exception as e:
                    print(f"[ERROR] Failed to load chat index for {session_id}: {e}, creating new")
                    self._chat_indices[session_id] = faiss.IndexFlatIP(self.dim)
            else:
                self._chat_indices[session_id] = faiss.IndexFlatIP(self.dim)
                print(f"[OK] Created new chat index for session {session_id}")
        else:
            print(f"[WARNING] Encoder not loaded, cannot create index for {session_id}")
        
        self._loaded_sessions.add(session_id)
    
    def _get_session_index(self, session_id: str) -> faiss.Index:
        """获取指定session的索引（懒加载）"""
        if session_id not in self._chat_indices:
            self._ensure_session_loaded(session_id)
        return self._chat_indices.get(session_id)
    
    def _get_session_chunks(self, session_id: str) -> List[Dict]:
        """获取指定session的chunks（懒加载）"""
        if session_id not in self._chat_chunks:
            self._ensure_session_loaded(session_id)
        return self._chat_chunks.get(session_id, [])
    
    def add_chat_atom(self, chunk: Dict, session_id: str) -> str:
        """
        添加对话原子块到指定session
        
        Args:
            chunk: 对话块数据
            session_id: 会话ID（必须指定，实现隔离）
        """
        if not self.encoder:
            raise RuntimeError("Encoder not loaded")
        
        if not session_id:
            raise ValueError("session_id is required for chat isolation")
        
        # 确保session目录存在
        session_dir = os.path.join(self.chat_dir, session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        # 懒加载session
        self._ensure_session_loaded(session_id)
        
        chunk_id = str(uuid.uuid4())[:8]
        
        atom_meta = {
            "chunk_id": chunk_id,
            "text": chunk["text"],
            "user_name": chunk.get("user_name", "用户"),
            "character_name": chunk.get("character_name", "AI"),
            "user_input": chunk.get("user_input", ""),
            "assistant_reply": chunk.get("assistant_reply", ""),
            "session_id": session_id,
            "timestamp": chunk["timestamp"],
            "source_type": "chat"
        }
        
        embedding = self._encode_texts([chunk["text"]])
        
        # 添加到该session的索引
        chat_index = self._get_session_index(session_id)
        chat_index.add(np.array(embedding).astype('float32'))
        
        # 添加到该session的chunks
        self._chat_chunks[session_id].append(atom_meta)
        
        # 保存该session的数据
        self._save_session_store(session_id)
        
        return chunk_id
    
    def search_chat_history(
        self,
        query: str,
        session_id: Optional[str] = None,
        k: int = 10
    ) -> List[Dict]:
        """
        检索对话历史
        现在只检索指定session的对话（实现隔离）
        """
        if not self.encoder:
            print(f"[WARNING] search_chat_history: encoder not loaded")
            return []
        
        if not session_id:
            print(f"[WARNING] search_chat_history: no session_id provided")
            return []
        
        chat_index = self._get_session_index(session_id)
        chat_chunks = self._get_session_chunks(session_id)
        
        if chat_index is None:
            print(f"[WARNING] search_chat_history: no index for session {session_id}")
            return []
        
        if chat_index.ntotal == 0:
            print(f"[INFO] search_chat_history: empty index for session {session_id}")
            return []
        
        query_vec = self._encode_texts([query])
        search_k = min(k * 2, chat_index.ntotal)
        D, I = chat_index.search(np.array(query_vec).astype('float32'), search_k)
        
        candidates = []
        results = []
        for idx, score in zip(I[0], D[0]):
            if idx == -1 or idx >= len(chat_chunks):
                continue
            chunk = chat_chunks[idx].copy()
            chunk["raw_score"] = float(score)
            chunk["is_same_session"] = True
            candidates.append(chunk)

        normalized_scores = self._compute_normalized_similarities(
            query,
            [chunk.get("text", "") for chunk in candidates]
        )

        for chunk, semantic_score in zip(candidates, normalized_scores):
            chunk["semantic_score"] = semantic_score
            chunk["score"] = semantic_score
            results.append(chunk)

        results.sort(key=lambda x: x["score"], reverse=True)
        print(f"[OK] search_chat_history for session {session_id}: found {len(results)} results")
        return results[:k]
    
    def _save_session_store(self, session_id: str):
        """保存指定session的数据"""
        try:
            session_dir = os.path.join(self.chat_dir, session_id)
            os.makedirs(session_dir, exist_ok=True)
            
            # 保存元数据
            meta_path = os.path.join(session_dir, "metadata.json")
            chunks = self._chat_chunks.get(session_id, [])
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(chunks, f, ensure_ascii=False, indent=2)
            
            # 保存索引
            chat_index = self._chat_indices.get(session_id)
            if chat_index:
                _faiss_write_index(chat_index, os.path.join(session_dir, "faiss.index"))
            
            print(f"[OK] Saved session {session_id}: {len(chunks)} chunks, {chat_index.ntotal if chat_index else 0} vectors")
        except Exception as e:
            print(f"[ERROR] Failed to save session {session_id}: {e}")
            import traceback
            traceback.print_exc()
    
    def delete_chat_session(self, session_id: str) -> bool:
        """删除整个session的对话数据和索引"""
        try:
            session_dir = os.path.join(self.chat_dir, session_id)
            if os.path.exists(session_dir):
                shutil.rmtree(session_dir)
            
            # 从内存中移除
            if session_id in self._chat_indices:
                del self._chat_indices[session_id]
            if session_id in self._chat_chunks:
                del self._chat_chunks[session_id]
            if session_id in self._loaded_sessions:
                self._loaded_sessions.remove(session_id)
            
            return True
        except Exception as e:
            print(f"[ERROR] Failed to delete chat session {session_id}: {e}")
            return False

    def clear_knowledge_store(self) -> bool:
        """Clear persisted and in-memory knowledge data."""
        try:
            meta_path = os.path.join(self.knowledge_dir, "metadata.json")
            index_path = os.path.join(self.knowledge_dir, "faiss.index")

            if os.path.exists(meta_path):
                os.remove(meta_path)
            if os.path.exists(index_path):
                os.remove(index_path)

            self.knowledge_chunks = []
            self.knowledge_index = faiss.IndexFlatIP(self.dim) if self.encoder else None
            return True
        except Exception as e:
            print(f"[ERROR] Failed to clear knowledge store: {e}")
            return False

    def _rebuild_knowledge_index(self):
        """重建知识库索引并同步 child_mappings。"""
        if not self.encoder:
            return

        self.knowledge_index = faiss.IndexFlatIP(self.dim)
        embeddings = []

        for chunk in self.knowledge_chunks:
            children = chunk.get("children", [chunk.get("text", "")])
            chunk["child_mappings"] = []
            for child_text in children:
                embedding = self._encode_texts([child_text])
                embeddings.append(embedding[0])
                chunk["child_mappings"].append(len(embeddings) - 1)

        if embeddings:
            self.knowledge_index.add(np.array(embeddings).astype('float32'))

    def delete_knowledge_chunk(self, chunk_id: str) -> bool:
        """按 chunk_id 删除知识块并重建索引。"""
        if not chunk_id:
            return False

        original_len = len(self.knowledge_chunks)
        self.knowledge_chunks = [
            chunk for chunk in self.knowledge_chunks
            if chunk.get("chunk_id") != chunk_id
        ]

        if len(self.knowledge_chunks) == original_len:
            return False

        self._rebuild_knowledge_index()
        self._save_knowledge_store()
        return True
    
    def delete_chat_chunks_by_session_and_round(self, session_id: str, round_num: int) -> List[str]:
        """删除指定session和轮次的对话块"""
        if not session_id:
            return []
        
        self._ensure_session_loaded(session_id)
        
        chat_chunks = self._get_session_chunks(session_id)
        deleted_ids = []
        indices_to_remove = []
        
        for i, chunk in enumerate(chat_chunks):
            if chunk.get("timestamp", {}).get("round_num") == round_num:
                deleted_ids.append(chunk.get("chunk_id"))
                indices_to_remove.append(i)
        
        if not deleted_ids:
            return []
        
        # 从后往前删除
        for idx in sorted(indices_to_remove, reverse=True):
            chat_chunks.pop(idx)
        
        # 重建索引
        self._rebuild_session_index(session_id)
        
        # 保存
        self._save_session_store(session_id)
        
        return deleted_ids
    
    def _rebuild_session_index(self, session_id: str):
        """重建指定session的索引"""
        if not self.encoder:
            return
        
        chat_chunks = self._get_session_chunks(session_id)
        
        # 创建新索引
        new_index = faiss.IndexFlatIP(self.dim)
        
        # 重新编码所有chunks
        if chat_chunks:
            texts = [c["text"] for c in chat_chunks]
            embeddings = self._encode_texts(texts)
            new_index.add(np.array(embeddings).astype('float32'))
        
        self._chat_indices[session_id] = new_index
    
    def get_chat_chunks_by_session(self, session_id: str) -> List[Dict]:
        """获取指定session的所有对话块"""
        if not session_id:
            return []
        self._ensure_session_loaded(session_id)
        return self._get_session_chunks(session_id).copy()
    
    def get_session_stats(self, session_id: str) -> Dict:
        """获取指定session的统计信息"""
        if not session_id:
            return {"count": 0}
        
        self._ensure_session_loaded(session_id)
        chat_index = self._get_session_index(session_id)
        
        return {
            "count": len(self._get_session_chunks(session_id)),
            "vectors": chat_index.ntotal if chat_index else 0
        }
    
    # ==================== 知识库持久化 ====================
    
    def _save_knowledge_store(self):
        """保存知识库数据"""
        with open(os.path.join(self.knowledge_dir, "metadata.json"), 'w', encoding='utf-8') as f:
            json.dump(self.knowledge_chunks, f, ensure_ascii=False, indent=2)
        
        if self.knowledge_index:
            _faiss_write_index(self.knowledge_index, os.path.join(self.knowledge_dir, "faiss.index"))
    
    def _load_knowledge_store(self):
        """加载知识库数据"""
        meta_path = os.path.join(self.knowledge_dir, "metadata.json")
        index_path = os.path.join(self.knowledge_dir, "faiss.index")
        
        print(f"[Knowledge] Loading from {self.knowledge_dir}")
        print(f"[Knowledge] Metadata exists: {os.path.exists(meta_path)}")
        print(f"[Knowledge] Index exists: {os.path.exists(index_path)}")
        
        if os.path.exists(meta_path):
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    self.knowledge_chunks = json.load(f)
                print(f"[Knowledge] Loaded {len(self.knowledge_chunks)} chunks from metadata")
            except Exception as e:
                print(f"[ERROR] Failed to load knowledge metadata: {e}")
                self.knowledge_chunks = []
        else:
            print(f"[Knowledge] No metadata file found")
            self.knowledge_chunks = []
        
        if os.path.exists(index_path) and self.encoder:
            try:
                self.knowledge_index = _faiss_read_index(index_path)
                print(f"[OK] Loaded knowledge index: {self.knowledge_index.ntotal} vectors")
                
                # 重建 child_mappings（因为索引向量顺序可能与保存时不同）
                self._rebuild_child_mappings()
                
            except Exception as e:
                print(f"[ERROR] Failed to load knowledge index: {e}")
                self.knowledge_index = faiss.IndexFlatIP(self.dim)
        elif self.encoder:
            print(f"[Knowledge] Creating new empty index")
            self.knowledge_index = faiss.IndexFlatIP(self.dim)
    
    def _rebuild_child_mappings(self):
        """重建子块到父块的映射"""
        if not self.knowledge_chunks or not self.knowledge_index:
            return
        
        print(f"[Knowledge] Rebuilding child mappings...")
        
        # 统计所有子块
        total_children = 0
        for chunk in self.knowledge_chunks:
            children = chunk.get("children", [chunk.get("text", "")])
            total_children += len(children)
        
        print(f"[Knowledge] Total children: {total_children}, Index vectors: {self.knowledge_index.ntotal}")
        
        # 重建映射（假设向量顺序与子块顺序一致）
        vector_idx = 0
        for p_idx, chunk in enumerate(self.knowledge_chunks):
            children = chunk.get("children", [chunk.get("text", "")])
            chunk["child_mappings"] = []
            for _ in children:
                if vector_idx < self.knowledge_index.ntotal:
                    chunk["child_mappings"].append(vector_idx)
                    vector_idx += 1
        
        print(f"[Knowledge] Rebuilt mappings for {len(self.knowledge_chunks)} parent chunks")
    
    # ==================== 数据迁移 ====================
    
    def _migrate_old_chat_data(self):
        """
        从旧版单一文件存储迁移到多会话隔离存储
        旧版: vector_db/chat/metadata.json + faiss.index (全局)
        新版: vector_db/chat/{session_id}/metadata.json + faiss.index (隔离)
        """
        old_meta_path = os.path.join(self.chat_dir, "metadata.json")
        old_index_path = os.path.join(self.chat_dir, "faiss.index")
        
        # 检查是否存在旧数据
        if not os.path.exists(old_meta_path):
            return  # 没有旧数据，无需迁移
        
        # 检查是否已经有新格式的数据（有子文件夹）
        has_new_format = any(
            os.path.isdir(os.path.join(self.chat_dir, d)) 
            for d in os.listdir(self.chat_dir) 
            if os.path.isdir(os.path.join(self.chat_dir, d))
        )
        
        if has_new_format:
            print("[INFO] New format data exists, skipping migration")
            return
        
        print("[MIGRATE] Found old chat data, migrating to new format...")
        
        try:
            # 读取旧元数据
            with open(old_meta_path, 'r', encoding='utf-8') as f:
                old_chunks = json.load(f)
            
            # 按 session_id 分组
            session_chunks = {}
            for chunk in old_chunks:
                sid = chunk.get('session_id', 'unknown')
                if sid not in session_chunks:
                    session_chunks[sid] = []
                session_chunks[sid].append(chunk)
            
            print(f"[MIGRATE] Found {len(old_chunks)} chunks from {len(session_chunks)} sessions")
            
            # 如果存在旧索引，尝试读取
            old_index = None
            if os.path.exists(old_index_path) and self.encoder:
                try:
                    old_index = _faiss_read_index(old_index_path)
                    print(f"[MIGRATE] Loaded old index with {old_index.ntotal} vectors")
                except Exception as e:
                    print(f"[MIGRATE] Failed to load old index: {e}")
            
            # 为每个会话创建新的存储
            for sid, chunks in session_chunks.items():
                if sid == 'unknown' or not sid:
                    continue
                
                # 创建会话目录
                session_dir = os.path.join(self.chat_dir, sid)
                os.makedirs(session_dir, exist_ok=True)
                
                # 保存元数据
                with open(os.path.join(session_dir, "metadata.json"), 'w', encoding='utf-8') as f:
                    json.dump(chunks, f, ensure_ascii=False, indent=2)
                
                # 如果有旧索引且能匹配，提取对应的向量
                if old_index and self.encoder:
                    # 重建索引（更安全，避免索引不匹配问题）
                    new_index = faiss.IndexFlatIP(self.dim)
                    texts = [c.get('text', '') for c in chunks]
                    if texts:
                        embeddings = self._encode_texts(texts)
                        new_index.add(np.array(embeddings).astype('float32'))
                        _faiss_write_index(new_index, os.path.join(session_dir, "faiss.index"))
                        print(f"[MIGRATE] Session {sid}: {len(chunks)} chunks, {new_index.ntotal} vectors")
                elif self.encoder:
                    # 没有旧索引，重新编码
                    new_index = faiss.IndexFlatIP(self.dim)
                    texts = [c.get('text', '') for c in chunks]
                    if texts:
                        embeddings = self._encode_texts(texts)
                        new_index.add(np.array(embeddings).astype('float32'))
                        _faiss_write_index(new_index, os.path.join(session_dir, "faiss.index"))
                        print(f"[MIGRATE] Session {sid}: {len(chunks)} chunks (re-encoded)")
            
            # 备份旧文件
            backup_dir = os.path.join(self.chat_dir, "_backup_old_format")
            os.makedirs(backup_dir, exist_ok=True)
            shutil.move(old_meta_path, os.path.join(backup_dir, "metadata.json"))
            if os.path.exists(old_index_path):
                shutil.move(old_index_path, os.path.join(backup_dir, "faiss.index"))
            
            print(f"[MIGRATE] Complete! Old data backed up to {backup_dir}")
            
        except Exception as e:
            print(f"[ERROR] Migration failed: {e}")
            import traceback
            traceback.print_exc()
    
    # ==================== 管理接口 ====================
    
    def get_all_session_ids(self) -> List[str]:
        """获取所有有对话数据的session_id列表"""
        sessions = []
        if os.path.exists(self.chat_dir):
            for item in os.listdir(self.chat_dir):
                item_path = os.path.join(self.chat_dir, item)
                if os.path.isdir(item_path):
                    # 检查是否有metadata.json
                    if os.path.exists(os.path.join(item_path, "metadata.json")):
                        sessions.append(item)
        return sessions
    
    def get_knowledge_stats(self) -> Dict:
        """获取知识库统计"""
        return {
            "total_vectors": self.knowledge_index.ntotal if self.knowledge_index else 0,
            "total_parents": len(self.knowledge_chunks),
            "total_chunks": len(self.knowledge_chunks)  # 兼容旧字段
        }
    
    def get_chat_stats(self) -> Dict:
        """获取对话历史统计"""
        session_ids = self.get_all_session_ids()
        total_vectors = 0
        for sid in session_ids:
            idx = self._get_session_index(sid)
            if idx:
                total_vectors += idx.ntotal
        
        return {
            "total_sessions": len(session_ids),
            "total_vectors": total_vectors
        }

    def get_global_stats(self) -> Dict:
        """获取全局统计"""
        knowledge_count = self.knowledge_index.ntotal if self.knowledge_index else 0
        session_ids = self.get_all_session_ids()
        
        return {
            "knowledge_vectors": knowledge_count,
            "knowledge_chunks": len(self.knowledge_chunks),
            "chat_sessions": len(session_ids),
            "total_chat_vectors": sum(
                self._get_session_index(sid).ntotal if sid in self._chat_indices 
                else self.get_session_stats(sid).get("vectors", 0)
                for sid in session_ids
            )
        }


# 全局实例
vector_store = DualVectorStore()
