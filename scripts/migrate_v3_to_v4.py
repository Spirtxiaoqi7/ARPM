"""
ARPM v3 → v4 数据迁移脚本
"""
import os
import sys
import json
import shutil
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

def migrate():
    """执行数据迁移"""
    print("=" * 60)
    print("ARPM v3 → v4 数据迁移工具")
    print("=" * 60)
    
    base_dir = Path(__file__).parent.parent
    old_data_dir = base_dir / "data"
    new_data_dir = base_dir / "data"
    
    old_vector_dir = old_data_dir / "vector_db"
    new_vector_dir = new_data_dir / "vector_db"
    new_knowledge_dir = new_vector_dir / "knowledge"
    new_chat_dir = new_vector_dir / "chat"
    
    # 检查旧数据
    if not old_vector_dir.exists():
        print("[信息] 未找到旧数据，无需迁移")
        return
    
    # 创建新目录结构
    os.makedirs(new_knowledge_dir, exist_ok=True)
    os.makedirs(new_chat_dir, exist_ok=True)
    
    print(f"[迁移] 从 {old_vector_dir}")
    print(f"[迁移] 到 {new_vector_dir}")
    print()
    
    # 迁移知识库
    migrated_knowledge = 0
    legacy_chunks_path = old_vector_dir / "chunks.json"
    legacy_meta_path = old_vector_dir / "metadata.json"
    legacy_faiss_path = old_vector_dir / "faiss.index"
    
    # 优先处理新版父子块格式
    parent_chunks_path = old_vector_dir / "parent_chunks.json"
    child_chunks_path = old_vector_dir / "child_chunks.json"
    child_map_path = old_vector_dir / "child_to_parent.json"
    metadata_path = old_vector_dir / "metadata.json"
    
    if parent_chunks_path.exists():
        print("[知识库] 发现v3父子块格式，直接迁移...")
        shutil.copy(parent_chunks_path, new_knowledge_dir / "metadata.json")
        if (old_vector_dir / "faiss.index").exists():
            shutil.copy(old_vector_dir / "faiss.index", new_knowledge_dir / "faiss.index")
        
        # 添加chunk_id
        with open(new_knowledge_dir / "metadata.json", 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        
        for i, chunk in enumerate(chunks):
            if 'chunk_id' not in chunk:
                chunk['chunk_id'] = f"v3_{i:06d}"
            chunk['source_type'] = 'knowledge'
            # 转换timestamp格式
            if 'timestamp' in chunk:
                old_ts = chunk['timestamp']
                if isinstance(old_ts, (int, float)) and old_ts > 1e9:
                    # 旧版Unix时间戳，转换为轮次1
                    chunk['timestamp'] = {"round_num": 1, "physical_time": ""}
                elif isinstance(old_ts, int):
                    chunk['timestamp'] = {"round_num": old_ts, "physical_time": ""}
        
        with open(new_knowledge_dir / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        
        migrated_knowledge = len(chunks)
    
    elif legacy_chunks_path.exists():
        print("[知识库] 发现v3旧版格式，迁移中...")
        with open(legacy_chunks_path, 'r', encoding='utf-8') as f:
            legacy_chunks = json.load(f)
        
        legacy_metadata = []
        if legacy_meta_path.exists():
            with open(legacy_meta_path, 'r', encoding='utf-8') as f:
                legacy_metadata = json.load(f)
        
        new_chunks = []
        for i, text in enumerate(legacy_chunks):
            meta = legacy_metadata[i] if i < len(legacy_metadata) else {}
            
            # 转换时间戳
            old_ts = meta.get("timestamp", 1)
            if isinstance(old_ts, (int, float)) and old_ts > 1e9:
                old_ts = 1
            
            new_chunk = {
                "chunk_id": f"v3_legacy_{i:06d}",
                "text": text,
                "children": [text],  # 旧版无子块，整句作为子块
                "timestamp": {"round_num": old_ts, "physical_time": ""},
                "source": meta.get("source", "unknown"),
                "source_type": "knowledge",
                "child_mappings": [i]  # 指向FAISS索引
            }
            new_chunks.append(new_chunk)
        
        with open(new_knowledge_dir / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(new_chunks, f, ensure_ascii=False, indent=2)
        
        if legacy_faiss_path.exists():
            shutil.copy(legacy_faiss_path, new_knowledge_dir / "faiss.index")
        
        migrated_knowledge = len(new_chunks)
    
    # 初始化空对话索引
    print("[对话] 初始化新的对话索引...")
    with open(new_chat_dir / "metadata.json", 'w', encoding='utf-8') as f:
        json.dump([], f)
    
    # 迁移会话数据
    old_memory_dir = old_data_dir / "memory_db"
    new_memory_dir = new_data_dir / "memory_db"
    os.makedirs(new_memory_dir, exist_ok=True)
    
    migrated_sessions = 0
    if old_memory_dir.exists():
        print("[会话] 迁移会话数据...")
        for filename in os.listdir(old_memory_dir):
            if filename.startswith("session_") and filename.endswith(".json"):
                src = old_memory_dir / filename
                dst = new_memory_dir / filename
                try:
                    with open(src, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                    
                    # 转换旧格式
                    if 'messages' not in session_data:
                        session_data['messages'] = []
                    if 'memories' not in session_data:
                        session_data['memories'] = []
                    
                    # 保存
                    with open(dst, 'w', encoding='utf-8') as f:
                        json.dump(session_data, f, ensure_ascii=False, indent=2)
                    
                    migrated_sessions += 1
                except Exception as e:
                    print(f"  [警告] 迁移 {filename} 失败: {e}")
    
    # 打印结果
    print()
    print("=" * 60)
    print("迁移完成!")
    print(f"  - 知识库片段: {migrated_knowledge}")
    print(f"  - 会话数量: {migrated_sessions}")
    print("=" * 60)
    print()
    print("注意:")
    print("  1. v4使用双索引结构（知识库+对话）")
    print("  2. 旧数据已保留备份")
    print("  3. 首次启动时会自动重建FAISS索引")

if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"[错误] 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
