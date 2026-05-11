"""
文本分块 - 父子块结构
"""
from typing import List, Dict, Optional
from utils.text_utils import TextProcessor

class Chunker:
    """递归中文分块器"""
    
    def __init__(self, child_size: int = 200, parent_size: int = 600, overlap: int = 1):
        self.child_size = child_size
        self.parent_size = parent_size
        self.overlap = overlap
        self.processor = TextProcessor()
    
    def create_knowledge_chunks(
        self,
        text: str,
        source: str = "upload",
        timestamp: Optional[Dict] = None
    ) -> List[Dict]:
        """
        创建知识库父子块
        
        Returns:
            List[Dict]: 父块列表，每个包含children字段
        """
        sentences = self.processor.split_sentences(text)
        if not sentences:
            return []
        
        # 创建子块
        child_chunks = self._make_chunks(sentences, self.child_size)
        if not child_chunks:
            return []
        
        # 子块组合成父块
        parent_chunks = []
        i = 0
        while i < len(child_chunks):
            parent_text = ""
            child_indices = []
            j = i
            
            while j < len(child_chunks) and len(parent_text) + len(child_chunks[j]) <= self.parent_size:
                parent_text += child_chunks[j]
                child_indices.append(j)
                j += 1
            
            if not parent_text:
                parent_text = child_chunks[i][:self.parent_size]
                child_indices = [i]
                j = i + 1
            
            parent_chunks.append({
                "text": parent_text,
                "children": [child_chunks[idx] for idx in child_indices],
                "metadata": {
                    "source": source,
                    "timestamp": timestamp or {"round_num": 1, "physical_time": ""},
                    "child_count": len(child_indices)
                }
            })
            
            # 重叠
            i = max(i + 1, j - self.overlap)
        
        return parent_chunks
    
    def create_chat_atom(
        self,
        content: str,
        role: str,
        session_id: str,
        round_num: int,
        physical_time: str
    ) -> Dict:
        """
        创建对话原子块（不再分块，整句作为原子）
        
        Args:
            content: 对话内容
            role: user/assistant
            session_id: 会话ID
            round_num: 轮次
            physical_time: 物理时间
        
        Returns:
            Dict: 原子块结构
        """
        return {
            "text": content,
            "source": "chat",
            "role": role,
            "session_id": session_id,
            "timestamp": {
                "round_num": round_num,
                "physical_time": physical_time
            },
            # 对话原子块没有children，直接存储
            "is_atom": True
        }
    
    def _make_chunks(self, sentences: List[str], target_size: int) -> List[str]:
        """将句子组合成目标大小的块"""
        chunks = []
        i = 0
        max_iter = len(sentences) * 2
        iter_count = 0
        
        while i < len(sentences) and iter_count < max_iter:
            iter_count += 1
            chunk_text = ""
            j = i
            
            while j < len(sentences) and len(chunk_text) + len(sentences[j]) <= target_size:
                chunk_text += sentences[j]
                j += 1
            
            if not chunk_text:
                chunk_text = sentences[i][:target_size]
                j = i + 1
            
            chunks.append(chunk_text)
            
            if j < len(sentences):
                i = max(i + 1, j - self.overlap)
            else:
                break
        
        return chunks
