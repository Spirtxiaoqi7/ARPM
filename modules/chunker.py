"""
文本分块模块 — 支持父子块结构的递归中文分块
"""

import re
from typing import List, Dict, Optional



class Chunker:
    def __init__(self, child_size: int = 200, parent_size: int = 600, overlap_sentences: int = 1):
        self.child_size = child_size
        self.parent_size = parent_size
        self.overlap_sentences = overlap_sentences

    def split_sentences(self, text: str) -> List[str]:
        """按中文句末标点拆分句子"""
        sentences = re.split(r'(?<=[。！？；\n])\s*', text)
        return [s.strip() for s in sentences if s.strip()]

    def _make_chunks(self, sentences: List[str], target_size: int) -> List[str]:
        """将句子组合成目标大小的块"""
        if not sentences:
            return []
        
        chunks = []
        i = 0
        max_iter = len(sentences) * 2  # 循环预防
        iter_count = 0
        
        while i < len(sentences) and iter_count < max_iter:
            iter_count += 1
            chunk_text = ""
            j = i
            
            while j < len(sentences) and len(chunk_text) + len(sentences[j]) <= target_size:
                chunk_text += sentences[j]
                j += 1
            
            if not chunk_text:
                # 单个句子超过目标大小，强行截断
                chunk_text = sentences[i][:target_size]
                j = i + 1
            
            chunks.append(chunk_text)
            
            if j < len(sentences):
                # 保持1句重叠以维护连贯性
                i = max(i + 1, j - self.overlap_sentences)
            else:
                break
        
        return chunks

    def split_text(self, text: str, metadata: Optional[Dict] = None, current_round: int = 1) -> List[Dict]:
        """
        递归中文分块：生成父子块结构
        - 子块(~200字符)：用于语义精度检索
        - 父块(~600字符)：由相邻子块组成，用于上下文完整性
        
        timestamp 记录对话轮次（current_round），以支持 ARPM 轮次差衰减。
        """
        if not text:
            return []
        
        sentences = self.split_sentences(text)
        if not sentences:
            return []
        
        base_meta = {
            "timestamp": current_round,
            "source": metadata.get("source") if metadata else "upload",
            "permanent": metadata.get("permanent", False) if metadata else False
        }
        
        # 阶段1：生成子块
        child_chunks = self._make_chunks(sentences, self.child_size)
        if not child_chunks:
            return []
        
        # 阶段2：由子块生成父块（约3个子块组合成600字符）
        parent_chunks = []
        parent_child_map = []  # 记录每个父块包含哪些子块索引
        
        i = 0
        max_iter = len(child_chunks) * 2
        iter_count = 0
        
        while i < len(child_chunks) and iter_count < max_iter:
            iter_count += 1
            parent_text = ""
            j = i
            
            while j < len(child_chunks) and len(parent_text) + len(child_chunks[j]) <= self.parent_size:
                parent_text += child_chunks[j]
                j += 1
            
            if not parent_text:
                parent_text = child_chunks[i][:self.parent_size]
                j = i + 1
            
            parent_chunks.append(parent_text)
            parent_child_map.append(list(range(i, j)))
            
            if j < len(child_chunks):
                # 父块之间保持1个子块重叠
                i = max(i + 1, j - 1)
            else:
                break
        
        # 返回以父块为单位的列表，但内部关联子块
        results = []
        for p_idx, (parent_text, child_indices) in enumerate(zip(parent_chunks, parent_child_map)):
            # 提取该父块对应的子块文本
            children_texts = [child_chunks[c_idx] for c_idx in child_indices]
            
            results.append({
                "text": parent_text,  # 父块用于生成上下文
                "metadata": {
                    **base_meta,
                    "length": len(parent_text),
                    "parent_index": p_idx,
                    "children": children_texts,  # 子块用于检索匹配
                    "child_indices": child_indices,
                    "is_parent": True
                }
            })
        
        return results


chunker = Chunker()
