"""
BM25+ 实现 - 从 ARPM-v3 迁移优化
"""
import math
import re
import jieba
from typing import List, Dict
from collections import Counter

class PorterStemmer:
    """Porter Stemmer - 英文词干提取"""
    
    def __init__(self, cache_size: int = 10000):
        self.cache = {}
        self.cache_size = cache_size
    
    def stem(self, word: str) -> str:
        if not word or len(word) <= 2:
            return word.lower()
        word = word.lower()
        if word in self.cache:
            return self.cache[word]
        stem = self._do_stem(word)
        if len(self.cache) >= self.cache_size:
            self.cache.pop(next(iter(self.cache)))
        self.cache[word] = stem
        return stem
    
    def _do_stem(self, word: str) -> str:
        stem = word
        # Step 1a: 复数处理
        if stem.endswith('sses'):
            stem = stem[:-2]
        elif stem.endswith('ies'):
            stem = stem[:-2]
        elif stem.endswith('s') and not stem.endswith('ss'):
            stem = stem[:-1]
        # 简化版，完整版见v3
        return stem

class BM25PlusScorer:
    """BM25+ 评分器"""
    
    # 停用词
    STOP_WORDS = {
        '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '上', '也',
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    }
    
    def __init__(self, k1: float = 1.5, b: float = 0.75, delta: float = 0.5):
        self.k1 = k1
        self.b = b
        self.delta = delta
        self.stemmer = PorterStemmer()
        
        self.documents: List[str] = []
        self.doc_term_freqs: List[Counter] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_length = 0.0
        self.idf: Dict[str, float] = {}
        self.total_docs = 0
    
    def tokenize(self, text: str) -> List[str]:
        """中英文混合分词"""
        if not text:
            return []
        text = text.lower().strip()
        tokens = []
        
        # 英文部分
        for part in re.findall(r'[a-zA-Z]+', text):
            if part not in self.STOP_WORDS and len(part) >= 2:
                tokens.append(self.stemmer.stem(part))
        
        # 中文部分
        chinese_text = re.sub(r'[a-zA-Z]+', ' ', text)
        if chinese_text.strip():
            for token in jieba.cut(chinese_text):
                token = token.strip()
                if token and len(token) >= 2 and token not in self.STOP_WORDS:
                    tokens.append(token)
        
        return tokens
    
    def index_documents(self, documents: List[str]):
        """索引文档"""
        self.documents = documents
        self.total_docs = len(documents)
        self.doc_term_freqs = []
        self.doc_lengths = []
        
        total_length = 0
        for doc in documents:
            tokens = self.tokenize(doc)
            term_freq = Counter(tokens)
            self.doc_term_freqs.append(term_freq)
            self.doc_lengths.append(len(tokens))
            total_length += len(tokens)
        
        self.avg_doc_length = total_length / self.total_docs if self.total_docs > 0 else 0
        self._calculate_idf()
    
    def _calculate_idf(self):
        """计算IDF"""
        doc_freq = Counter()
        for term_freq in self.doc_term_freqs:
            for term in term_freq.keys():
                doc_freq[term] += 1
        
        self.idf = {}
        for term, df in doc_freq.items():
            raw_idf = math.log((self.total_docs - df + 0.5) / (df + 0.5))
            self.idf[term] = max(0, raw_idf) + self.delta
    
    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """搜索"""
        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []
        
        results = []
        for i in range(self.total_docs):
            score = self._score_document(query_tokens, i)
            if score > 0:
                results.append({
                    'index': i,
                    'score': score,
                    'document': self.documents[i]
                })
        
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]
    
    def _score_document(self, query_tokens: List[str], doc_idx: int) -> float:
        """计算单文档得分"""
        if self.avg_doc_length == 0:
            return 0.0
        
        term_freq = self.doc_term_freqs[doc_idx]
        doc_length = self.doc_lengths[doc_idx]
        
        score = 0.0
        for token in query_tokens:
            tf = term_freq.get(token, 0)
            if tf == 0:
                continue
            
            idf = self.idf.get(token, 0)
            tf_weight = tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * doc_length / self.avg_doc_length))
            score += idf * tf_weight
        
        return score
