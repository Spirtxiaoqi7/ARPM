"""
BM25+ 增强检索模块
基于 VectHare 的优秀实践，针对中文场景优化
"""

import math
import re
import jieba
from typing import List, Dict, Optional, Set, Tuple
from collections import Counter


# 中文停用词（扩展版）
CHINESE_STOP_WORDS = {
    # 基础停用词
    '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '那', '之', '与', '及', '等', '或',
    # 常见虚词
    '而且', '或者', '但是', '因为', '所以', '因此', '如果', '即使', '虽然', '尽管',
    '这样', '那样', '这里', '那里', '哪里', '什么', '怎么', '为什么', '如何', '谁',
    # 标点符号（会被预处理过滤）
}

# 英文停用词（190+词）
ENGLISH_STOP_WORDS = {
    'the', 'a', 'an', 'this', 'that', 'these', 'those', 'some', 'any', 'each',
    'every', 'both', 'either', 'neither', 'such', 'what', 'which', 'whose',
    'i', 'me', 'my', 'mine', 'myself', 'you', 'your', 'yours', 'yourself',
    'he', 'him', 'his', 'himself', 'she', 'her', 'hers', 'herself',
    'it', 'its', 'itself', 'we', 'us', 'our', 'ours', 'ourselves',
    'they', 'them', 'their', 'theirs', 'themselves',
    'who', 'whom', 'whoever', 'someone', 'anyone', 'everyone', 'nobody',
    'something', 'anything', 'everything', 'nothing',
    'and', 'or', 'but', 'nor', 'so', 'yet', 'for', 'because', 'although',
    'while', 'whereas', 'unless', 'until', 'since', 'when', 'whenever',
    'where', 'wherever', 'whether', 'if', 'then', 'than', 'as',
    'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'into', 'onto',
    'upon', 'out', 'off', 'over', 'under', 'above', 'below', 'between', 'among',
    'through', 'during', 'before', 'after', 'behind', 'beside', 'beyond',
    'within', 'without', 'about', 'around', 'against', 'along', 'across',
    'be', 'am', 'is', 'are', 'was', 'were', 'been', 'being',
    'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'done',
    'will', 'would', 'shall', 'should', 'may', 'might', 'must', 'can', 'could',
    'get', 'got', 'go', 'went', 'gone', 'come', 'came', 'take', 'took', 'taken',
    'make', 'made', 'say', 'said', 'know', 'knew', 'think', 'thought',
    'see', 'saw', 'seen', 'want', 'use', 'find', 'found', 'give', 'gave',
    'very', 'really', 'quite', 'just', 'only', 'even', 'also', 'still', 'already',
    'always', 'never', 'ever', 'often', 'sometimes', 'usually', 'now', 'then',
    'here', 'there', 'today', 'soon', 'again', 'much', 'more', 'most', 'less',
    'well', 'however', 'therefore', 'thus', 'too', 'enough',
    'good', 'great', 'best', 'better', 'bad', 'new', 'old', 'big', 'small',
    'large', 'little', 'long', 'short', 'high', 'low', 'same', 'different',
    'other', 'another', 'next', 'last', 'first', 'many', 'few', 'own',
    'thing', 'things', 'way', 'ways', 'place', 'part', 'case', 'point', 'fact',
    'like', 'back', 'time', 'year', 'day', 'one', 'two', 'three',
}

ALL_STOP_WORDS = CHINESE_STOP_WORDS | ENGLISH_STOP_WORDS


class PorterStemmer:
    """Porter Stemmer 实现 - 用于英文词干提取"""
    
    def __init__(self, cache_size: int = 10000):
        self.cache = {}
        self.cache_size = cache_size
        
    def stem(self, word: str) -> str:
        """提取词干"""
        if not word or len(word) <= 2:
            return word.lower()
        
        word = word.lower()
        
        # 检查缓存
        if word in self.cache:
            return self.cache[word]
        
        stem = self._do_stem(word)
        
        # 缓存结果（LRU）
        if len(self.cache) >= self.cache_size:
            self.cache.pop(next(iter(self.cache)))
        self.cache[word] = stem
        
        return stem
    
    def _do_stem(self, word: str) -> str:
        """实际的词干提取逻辑"""
        stem = word
        preserve_e = False
        
        # Step 1a: 处理复数
        if stem.endswith('sses'):
            stem = stem[:-2]
        elif stem.endswith('ies'):
            stem = stem[:-2]
        elif stem.endswith('ss'):
            pass
        elif stem.endswith('s'):
            stem = stem[:-1]
        
        # Step 1b: 处理 -ed 和 -ing
        has_vowel = lambda s: bool(re.search(r'[aeiou]', s))
        
        if stem.endswith('eed'):
            base = stem[:-3]
            if base:
                stem = base + 'ee'
                preserve_e = True
        elif stem.endswith('ed'):
            base = stem[:-2]
            if has_vowel(base):
                stem = base
                if stem.endswith(('at', 'bl', 'iz')):
                    stem += 'e'
                    preserve_e = True
                elif re.search(r'([^aeiouslz])\1$', stem):
                    stem = stem[:-1]
        elif stem.endswith('ing'):
            base = stem[:-3]
            if has_vowel(base):
                stem = base
                if stem.endswith(('at', 'bl', 'iz')):
                    stem += 'e'
                    preserve_e = True
                elif re.search(r'([^aeiouslz])\1$', stem):
                    stem = stem[:-1]
        
        # Step 2: 处理后缀替换
        step2_mappings = [
            ('ational', 'ate'), ('tional', 'tion'), ('enci', 'ence'), ('anci', 'ance'),
            ('izer', 'ize'), ('abli', 'able'), ('alli', 'al'), ('entli', 'ent'),
            ('eli', 'e'), ('ousli', 'ous'), ('ization', 'ize'), ('ation', 'ate'),
            ('ator', 'ate'), ('alism', 'al'), ('iveness', 'ive'), ('fulness', 'ful'),
            ('ousness', 'ous'), ('aliti', 'al'), ('iviti', 'ive'), ('biliti', 'ble'),
        ]
        for suffix, replacement in step2_mappings:
            if stem.endswith(suffix) and len(stem) > len(suffix) + 2:
                stem = stem[:-len(suffix)] + replacement
                if replacement.endswith('e'):
                    preserve_e = True
                break
        
        # Step 3: 更多后缀处理
        step3_mappings = [
            ('icate', 'ic'), ('ative', ''), ('alize', 'al'),
            ('iciti', 'ic'), ('ical', 'ic'), ('ful', ''), ('ness', ''),
        ]
        for suffix, replacement in step3_mappings:
            if stem.endswith(suffix) and len(stem) > len(suffix) + 2:
                stem = stem[:-len(suffix)] + replacement
                break
        
        # Step 4: 移除末尾的 'e'
        if stem.endswith('e') and len(stem) > 3 and not preserve_e:
            base = stem[:-1]
            vc_count = len(re.findall(r'[aeiou]+[^aeiou]+', base))
            is_cvc = bool(re.search(r'[^aeiou][aeiou][^aeiouxwy]$', base))
            if vc_count > 1 or (vc_count == 1 and not is_cvc):
                stem = base
        
        return stem


class BM25PlusScorer:
    """
    BM25+ 增强评分器
    
    特性：
    - Porter Stemmer 词干提取（英文）
    - 停用词过滤（中英双语）
    - 字段加权（标题、标签、内容）
    - 覆盖率奖励（全查询词匹配+10%）
    - BM25+ IDF 平滑（delta = 0.5）
    """
    
    DEFAULT_K1 = 1.5
    DEFAULT_B = 0.75
    DEFAULT_DELTA = 0.5
    
    def __init__(self, k1: float = 1.5, b: float = 0.75, delta: float = 0.5,
                 field_boosting: bool = True, coverage_bonus: bool = True,
                 use_stemmer: bool = True, remove_stopwords: bool = True):
        self.k1 = k1
        self.b = b
        self.delta = delta
        self.field_boosting = field_boosting
        self.coverage_bonus = coverage_bonus
        self.use_stemmer = use_stemmer
        self.remove_stopwords = remove_stopwords
        
        self.stemmer = PorterStemmer() if use_stemmer else None
        
        # 文档统计
        self.documents = []
        self.doc_term_freqs = []
        self.doc_lengths = []
        self.avg_doc_length = 0
        self.idf = {}
        self.total_docs = 0
    
    def tokenize(self, text: str, is_query: bool = False) -> List[str]:
        """
        智能分词 - 中英文混合处理
        
        Args:
            text: 输入文本
            is_query: 是否为查询（查询不分词，保持完整词）
        """
        if not text:
            return []
        
        # 统一转小写，去除多余空格和标点
        text = text.lower().strip()
        
        # 分离中英文
        # 中文使用 jieba，英文按空格分割
        tokens = []
        
        # 先处理英文部分（保持完整单词）
        english_parts = re.findall(r'[a-zA-Z]+', text)
        for part in english_parts:
            if self.remove_stopwords and part in ENGLISH_STOP_WORDS:
                continue
            if len(part) >= 2:
                if self.use_stemmer and len(part) > 3:
                    tokens.append(self.stemmer.stem(part))
                else:
                    tokens.append(part)
        
        # 处理中文部分
        chinese_text = re.sub(r'[a-zA-Z]+', ' ', text)
        if chinese_text.strip():
            chinese_tokens = list(jieba.cut(chinese_text))
            for token in chinese_tokens:
                token = token.strip()
                if not token or len(token) < 2:
                    continue
                if self.remove_stopwords and token in CHINESE_STOP_WORDS:
                    continue
                tokens.append(token)
        
        return tokens
    
    def index_documents(self, documents: List[Dict]):
        """
        索引文档
        
        Args:
            documents: 文档列表，每个文档包含：
                - text: 内容文本
                - title: 标题（可选）
                - tags: 标签列表（可选）
        """
        self.documents = documents
        self.total_docs = len(documents)
        self.doc_term_freqs = []
        self.doc_lengths = []
        
        total_length = 0
        
        for doc in documents:
            all_tokens = []
            content_tokens = []
            
            # 字段加权
            if self.field_boosting:
                # 标题加权 4x
                if doc.get('title'):
                    title_tokens = self.tokenize(doc['title'])
                    all_tokens.extend(title_tokens * 4)
                
                # 标签加权 4x
                if doc.get('tags'):
                    for tag in doc['tags']:
                        tag_tokens = self.tokenize(tag)
                        all_tokens.extend(tag_tokens * 4)
            
            # 内容 1x
            content_tokens = self.tokenize(doc.get('text', ''))
            all_tokens.extend(content_tokens)
            
            # 计算词频
            term_freq = Counter(all_tokens)
            self.doc_term_freqs.append(term_freq)
            
            # 文档长度（仅内容部分用于长度归一化）
            content_len = len(content_tokens)
            self.doc_lengths.append(content_len)
            total_length += content_len
        
        self.avg_doc_length = total_length / self.total_docs if self.total_docs > 0 else 0
        
        # 计算 IDF
        self._calculate_idf()
        
        print(f"[BM25+] Indexed {self.total_docs} documents, avg length: {self.avg_doc_length:.1f} tokens, "
              f"field_boosting={self.field_boosting}, coverage_bonus={self.coverage_bonus}")
    
    def _calculate_idf(self):
        """计算 IDF - 使用 BM25+ 公式"""
        doc_freq = Counter()
        
        for term_freq in self.doc_term_freqs:
            for term in term_freq.keys():
                doc_freq[term] += 1
        
        self.idf = {}
        for term, df in doc_freq.items():
            # BM25+ IDF: max(0, log((N - df + 0.5) / (df + 0.5))) + delta
            raw_idf = math.log((self.total_docs - df + 0.5) / (df + 0.5))
            self.idf[term] = max(0, raw_idf) + self.delta
    
    def score_document(self, query_tokens: List[str], doc_idx: int) -> Tuple[float, int]:
        """
        计算单个文档的 BM25+ 得分
        
        Returns:
            (score, matched_terms): 得分和匹配词数
        """
        if self.avg_doc_length == 0 or not query_tokens:
            return 0.0, 0
        
        if doc_idx < 0 or doc_idx >= self.total_docs:
            return 0.0, 0
        
        term_freq = self.doc_term_freqs[doc_idx]
        doc_length = self.doc_lengths[doc_idx]
        
        score = 0.0
        matched_terms = 0
        
        for token in query_tokens:
            raw_tf = term_freq.get(token, 0)
            if raw_tf == 0:
                continue
            
            matched_terms += 1
            
            # 使用对数 TF: log(1 + tf) 防止高频词主导
            tf = math.log(1 + raw_tf)
            
            idf = self.idf.get(token, 0)
            
            # 长度归一化
            length_norm = 1 - self.b + self.b * (doc_length / self.avg_doc_length)
            
            # BM25+ 得分
            term_score = idf * (tf * (self.k1 + 1)) / (tf + self.k1 * length_norm)
            score += term_score
        
        # 覆盖率奖励：所有查询词都匹配时 +10%
        if self.coverage_bonus and matched_terms == len(query_tokens) and len(query_tokens) > 0:
            score *= 1.1
        
        return score, matched_terms
    
    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        搜索文档
        
        Returns:
            排序后的结果列表，每个元素包含 index, score, document, matched_terms
        """
        query_tokens = self.tokenize(query, is_query=True)
        
        if not query_tokens:
            return []
        
        # 计算所有文档得分
        results = []
        for i in range(self.total_docs):
            score, matched = self.score_document(query_tokens, i)
            if score > 0:
                results.append({
                    'index': i,
                    'score': score,
                    'document': self.documents[i],
                    'matched_terms': matched,
                    'query_tokens': query_tokens
                })
        
        # 排序
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]
    
    def batch_score(self, query: str, doc_indices: List[int]) -> Dict[int, float]:
        """
        批量计算指定文档的得分（用于混合检索时）
        """
        query_tokens = self.tokenize(query, is_query=True)
        scores = {}
        
        for idx in doc_indices:
            score, _ = self.score_document(query_tokens, idx)
            scores[idx] = score
        
        return scores
