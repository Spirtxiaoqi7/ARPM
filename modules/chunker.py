"""
文本分块模块
"""

import re
from typing import List, Dict, Optional
from datetime import datetime


class Chunker:
    def __init__(self, chunk_size: int = 600, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_sentences(self, text: str) -> List[str]:
        sentences = re.split(r'(?<=[。！？；\n])\s*', text)
        return [s.strip() for s in sentences if s.strip()]

    def split_text(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        if not text:
            return []
        
        sentences = self.split_sentences(text)
        chunks = []
        current_time = datetime.now().timestamp()
        
        i = 0
        while i < len(sentences):
            chunk_text = ""
            j = i
            
            while j < len(sentences) and len(chunk_text) + len(sentences[j]) <= self.chunk_size:
                chunk_text += sentences[j]
                j += 1
            
            if not chunk_text:
                chunk_text = sentences[i][:self.chunk_size]
                j = i + 1
            
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "timestamp": current_time,
                    "length": len(chunk_text),
                    "source": metadata.get("source") if metadata else "upload",
                    "permanent": metadata.get("permanent", False) if metadata else False
                }
            })
            
            if j < len(sentences):
                i = max(i + 1, j - 1)
            else:
                break
        
        return chunks


chunker = Chunker()
