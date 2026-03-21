# api/rag_api.py
import os
import json
import numpy as np
import time
from typing import List, Optional, Dict, Any
from math import exp

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import faiss

# 中文分词和 BM25
import jieba
from rank_bm25 import BM25Okapi

# 重新使用 sentence-transformers
from sentence_transformers import SentenceTransformer

# ---------- 目录配置 ----------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VECTOR_DIR = os.path.join(BASE_DIR, "vectors")
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(VECTOR_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

print("=" * 60)
print("正在启动 RAG 服务...")
print(f"项目根目录: {BASE_DIR}")
print(f"向量存储目录: {VECTOR_DIR}")
print("=" * 60)

# ---------- 加载编码器模型（text2vec-base-chinese）----------
LOCAL_MODEL_PATH = os.path.join(
    BASE_DIR,
    "models",
    "shibing624",
    "text2vec-base-chinese"
)
print(f"正在从本地加载 text2vec-base-chinese 编码器...")
print(f"模型路径: {LOCAL_MODEL_PATH}")

if not os.path.exists(LOCAL_MODEL_PATH):
    print("❌ 模型路径不存在！请检查 models/shibing624/text2vec-base-chinese 目录。")
    exit(1)

try:
    encoder = SentenceTransformer(LOCAL_MODEL_PATH)
    dim = encoder.get_sentence_embedding_dimension()
    print(f"✅ 加载成功，向量维度: {dim}")
except Exception as e:
    print("❌ 编码器加载失败！")
    print(f"详细错误: {e}")
    exit(1)

# ---------- 初始化 FAISS 索引、文本块、元数据、BM25 ----------
index = faiss.IndexFlatIP(dim)
text_chunks = []
chunk_metadata = []           # 与 text_chunks 一一对应，存储每个块的元数据
tokenized_corpus = []
bm25 = None

# 配置文件路径
index_path = os.path.join(VECTOR_DIR, "faiss.index")
text_path = os.path.join(VECTOR_DIR, "chunks.json")
meta_path = os.path.join(VECTOR_DIR, "chunks_metadata.json")

# 尝试加载已有的索引和元数据
if os.path.exists(index_path) and os.path.exists(text_path) and os.path.exists(meta_path):
    try:
        index = faiss.read_index(index_path)
        with open(text_path, 'r', encoding='utf-8') as f:
            text_chunks = json.load(f)
        with open(meta_path, 'r', encoding='utf-8') as f:
            chunk_metadata = json.load(f)
        tokenized_corpus = [list(jieba.cut(chunk)) for chunk in text_chunks]
        bm25 = BM25Okapi(tokenized_corpus)
        print(f"✅ 加载现有索引，共 {len(text_chunks)} 个文本块")
    except Exception as e:
        print(f"⚠️ 加载索引失败，将创建新索引。错误: {e}")
        index = faiss.IndexFlatIP(dim)
        text_chunks = []
        chunk_metadata = []
        tokenized_corpus = []
        bm25 = None
else:
    print("ℹ️ 未找到现有索引，将创建新索引")

# ---------- 创建 FastAPI 应用 ----------
app = FastAPI(title="RAG 服务", description="提供向量检索和混合检索功能")

# ---------- 数据模型 ----------
class SearchRequest(BaseModel):
    query: str
    top_k: int = 5

class SearchHybridRequest(SearchRequest):
    current_round: int = 0   # 当前对话轮次，用于时间衰减

class SearchResult(BaseModel):
    text: str
    score: float
    index: int
    metadata: Optional[Dict[str, Any]] = None   # 可选返回元数据

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    time_ms: float

class AddDocumentRequest(BaseModel):
    chunks: List[str]
    metadata: Optional[List[Dict[str, Any]]] = None  # 每个块的元数据，至少含 timestamp

# ---------- 健康检查 ----------
@app.get("/health")
async def health():
    return {"status": "ok", "total_chunks": len(text_chunks), "vector_dim": dim}

# ---------- 纯向量检索 ----------
@app.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    if len(text_chunks) == 0:
        raise HTTPException(400, "向量库为空，请先添加文档")
    start = time.time()
    query = req.query[:500] if len(req.query) > 500 else req.query
    query_vec = encoder.encode([query], normalize_embeddings=True)
    scores, indices = index.search(query_vec, min(req.top_k, len(text_chunks)))
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx >= 0:
            results.append(SearchResult(
                text=text_chunks[idx],
                score=float(score),
                index=int(idx),
                metadata=chunk_metadata[idx] if idx < len(chunk_metadata) else None
            ))
    elapsed = (time.time() - start) * 1000
    return SearchResponse(query=query, results=results, time_ms=round(elapsed, 2))

# ---------- 混合检索（含时间衰减 + 永久块固定权重）----------
@app.post("/search_hybrid", response_model=SearchResponse)
async def search_hybrid(req: SearchHybridRequest):
    if len(text_chunks) == 0:
        raise HTTPException(400, "向量库为空，请先添加文档")
    if bm25 is None:
        raise HTTPException(500, "BM25 索引未初始化，请检查服务日志")
    start = time.time()
    query = req.query[:500] if len(req.query) > 500 else req.query

    # ---------- 配置参数 ----------
    PERMANENT_WEIGHT = 1.0          # 永久块固定权重
    DECAY_RATE = 20.0               # 衰减率（值越大衰减越慢）
    MIN_RESULTS = 3                 # 最少返回结果数，不足时从永久块补充
    # -----------------------------

    # 1. 向量检索
    query_vec = encoder.encode([query], normalize_embeddings=True)
    vec_scores, vec_indices = index.search(query_vec, req.top_k * 2)

    # 2. BM25 检索
    tokenized_query = list(jieba.cut(query))
    bm25_scores = bm25.get_scores(tokenized_query)
    bm25_indices = np.argsort(bm25_scores)[-req.top_k * 2:][::-1]

    # 3. 融合得分（向量 + BM25）
    combined = {}
    for idx, score in zip(vec_indices[0], vec_scores[0]):
        combined[idx] = combined.get(idx, 0) + 0.6 * score
    max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1
    for idx in bm25_indices:
        if idx < len(text_chunks):
            combined[idx] = combined.get(idx, 0) + 0.4 * (bm25_scores[idx] / max_bm25)

    # 4. 计算时间权重（永久块固定权重，非永久块指数衰减）
    current_round = req.current_round
    time_weighted = {}
    permanent_indices = []  # 记录永久块的索引

    for idx, score in combined.items():
        if idx < len(chunk_metadata):
            meta = chunk_metadata[idx]
            timestamp = meta.get("timestamp", 0)
            permanent = meta.get("permanent", False)  # 假设元数据中可能有 permanent 字段

            if permanent:
                # 永久块不受时间衰减影响
                time_weighted[idx] = score * PERMANENT_WEIGHT
                permanent_indices.append(idx)
            else:
                rel_time = timestamp - current_round
                time_weight = exp(-abs(rel_time) / DECAY_RATE)
                time_weighted[idx] = score * time_weight
        else:
            # 无元数据的旧块，当作普通块处理
            time_weighted[idx] = score * exp(-abs(0 - current_round) / DECAY_RATE)

    # 5. 取 top_k
    sorted_idx = sorted(time_weighted.keys(), key=lambda i: time_weighted[i], reverse=True)[:req.top_k]

    # 6. 如果结果太少，从永久块中补充（排除已选中的）
    if len(sorted_idx) < MIN_RESULTS and permanent_indices:
        # 按 combined 得分降序排序（语义相关度）
        remaining = [i for i in permanent_indices if i not in sorted_idx]
        remaining.sort(key=lambda i: combined.get(i, 0), reverse=True)
        needed = MIN_RESULTS - len(sorted_idx)
        sorted_idx.extend(remaining[:needed])

    results = []
    for i in sorted_idx:
        meta = chunk_metadata[i] if i < len(chunk_metadata) else None
        results.append(SearchResult(
            text=text_chunks[i],
            score=float(time_weighted[i]),
            index=i,
            metadata=meta
        ))

    elapsed = (time.time() - start) * 1000
    return SearchResponse(query=query, results=results, time_ms=round(elapsed, 2))

# ---------- 添加文档 ----------
@app.post("/add_document")
async def add_document(req: AddDocumentRequest):
    global index, text_chunks, chunk_metadata, tokenized_corpus, bm25
    chunks = req.chunks
    metadata = req.metadata

    if not chunks:
        raise HTTPException(400, "chunks 不能为空")

    # 过滤空字符串
    chunks = [c for c in chunks if c.strip()]
    if not chunks:
        raise HTTPException(400, "所有块均为空")

    # 如果提供了元数据，长度必须与 chunks 一致
    if metadata is not None and len(metadata) != len(chunks):
        raise HTTPException(400, "metadata 长度必须与 chunks 一致")

    # 如果没有提供元数据，为每个块生成默认元数据（timestamp=0, tags=[]）
    if metadata is None:
        metadata = [{"timestamp": 0, "tags": []} for _ in chunks]
    else:
        # 确保每个元数据至少包含 timestamp
        for i, m in enumerate(metadata):
            if "timestamp" not in m:
                raise HTTPException(400, f"第 {i} 个块的 metadata 缺少 timestamp 字段")

    try:
        vectors = encoder.encode(chunks, normalize_embeddings=True)
    except Exception as e:
        raise HTTPException(500, f"向量化失败: {e}")

    index.add(vectors.astype(np.float32))
    text_chunks.extend(chunks)
    chunk_metadata.extend(metadata)

    # 更新 BM25 索引
    new_tokenized = [list(jieba.cut(chunk)) for chunk in chunks]
    tokenized_corpus.extend(new_tokenized)
    bm25 = BM25Okapi(tokenized_corpus)

    # 原子写入
    tmp_index = os.path.join(VECTOR_DIR, "faiss.tmp")
    tmp_text = os.path.join(VECTOR_DIR, "chunks.tmp")
    tmp_meta = os.path.join(VECTOR_DIR, "chunks_metadata.tmp")
    index_path = os.path.join(VECTOR_DIR, "faiss.index")
    text_path = os.path.join(VECTOR_DIR, "chunks.json")
    meta_path = os.path.join(VECTOR_DIR, "chunks_metadata.json")

    try:
        faiss.write_index(index, tmp_index)
        with open(tmp_text, 'w', encoding='utf-8') as f:
            json.dump(text_chunks, f, ensure_ascii=False, indent=2)
        with open(tmp_meta, 'w', encoding='utf-8') as f:
            json.dump(chunk_metadata, f, ensure_ascii=False, indent=2)
        os.replace(tmp_index, index_path)
        os.replace(tmp_text, text_path)
        os.replace(tmp_meta, meta_path)
    except Exception as e:
        # 写入失败，尝试回滚
        if os.path.exists(index_path) and os.path.exists(text_path) and os.path.exists(meta_path):
            try:
                index = faiss.read_index(index_path)
                with open(text_path, 'r', encoding='utf-8') as f:
                    text_chunks = json.load(f)
                with open(meta_path, 'r', encoding='utf-8') as f:
                    chunk_metadata = json.load(f)
                tokenized_corpus = [list(jieba.cut(chunk)) for chunk in text_chunks]
                bm25 = BM25Okapi(tokenized_corpus)
            except:
                index = faiss.IndexFlatIP(dim)
                text_chunks = []
                chunk_metadata = []
                tokenized_corpus = []
                bm25 = None
        else:
            index = faiss.IndexFlatIP(dim)
            text_chunks = []
            chunk_metadata = []
            tokenized_corpus = []
            bm25 = None
        raise HTTPException(500, f"写入索引文件失败: {e}")

    return {"status": "success", "added": len(chunks), "total": len(text_chunks)}

# ---------- 统计信息 ----------
@app.get("/stats")
async def stats():
    return {"total_chunks": len(text_chunks), "vector_dim": dim}

if __name__ == "__main__":
    print("请使用 uvicorn 启动服务：uvicorn rag_api:app --reload --host 0.0.0.0 --port 8003")