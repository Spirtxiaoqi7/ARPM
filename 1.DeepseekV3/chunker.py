#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
中文智能分块插件（修复版）
- 修复了死循环问题
- 增强了对重叠句子的处理，确保索引永远前进
- 保留原有功能：递归分块、质量查验、父子块
- 新增：分批发送到RAG（每批500块），避免超时
- 新增：支持为导入的文档设置统一时间戳（--timestamp），用于时间轴X轴
"""

import re
import os
import sys
import argparse
import requests
from typing import List, Tuple, Optional

# ---------------------------- 核心分块函数 ----------------------------

def split_sentences(text: str) -> List[str]:
    sentences = re.split(r'(?<=[。！？；\n])\s*', text)
    return [s.strip() for s in sentences if s.strip()]

def split_subclauses(sentence: str, max_len: int = 50) -> List[str]:
    stack = [sentence]
    result = []

    while stack:
        part = stack.pop()
        if len(part) <= max_len:
            result.append(part.strip())
            continue

        subparts = re.split(r'(?<=[，、])\s*', part)
        if len(subparts) == 1:
            result.append(part[:max_len].strip())
            remaining = part[max_len:].strip()
            if remaining:
                stack.append(remaining)
        else:
            for sub in reversed(subparts):
                if sub.strip():
                    stack.append(sub)

    return result

def recursive_chunk_by_sentences(
    text: str,
    target_chars: int = 250,
    overlap_sentences: int = 1,
    min_chunk_chars: int = 50,
    split_long_sentences: bool = True
) -> List[str]:
    paragraphs = re.split(r'\n\s*\n', text)
    all_sentences = []
    for para in paragraphs:
        if not para.strip():
            continue
        sentences = split_sentences(para)
        if split_long_sentences:
            expanded = []
            for sent in sentences:
                expanded.extend(split_subclauses(sent, target_chars // 2))
            sentences = expanded
        all_sentences.extend(sentences)

    if not all_sentences:
        return []

    chunks = []
    i = 0
    max_iter = len(all_sentences) * 2
    iter_count = 0
    while i < len(all_sentences) and iter_count < max_iter:
        iter_count += 1
        current_chunk = ""
        j = i
        while j < len(all_sentences) and len(current_chunk) + len(all_sentences[j]) <= target_chars:
            current_chunk += all_sentences[j]
            j += 1
        if not current_chunk:
            current_chunk = all_sentences[i][:target_chars]
            j = i + 1
        if len(current_chunk) < min_chunk_chars and j < len(all_sentences):
            current_chunk += all_sentences[j]
            j += 1
        chunks.append(current_chunk)
        next_i = j - overlap_sentences
        if next_i <= i:
            next_i = i + 1
        i = next_i

    if len(chunks) > 1 and len(chunks[-1]) < min_chunk_chars:
        chunks[-2] += chunks[-1]
        chunks.pop()

    return chunks

def generate_parent_child_chunks(
    text: str,
    child_chars: int = 200,
    parent_chars: int = 600,
    overlap_sentences: int = 1
) -> Tuple[List[str], List[str]]:
    sub_chunks = recursive_chunk_by_sentences(
        text, target_chars=child_chars, overlap_sentences=overlap_sentences
    )
    parent_chunks = recursive_chunk_by_sentences(
        text, target_chars=parent_chars, overlap_sentences=overlap_sentences
    )
    return sub_chunks, parent_chunks

def validate_chunks(chunks: List[str], min_chars: int = 20, max_chars: int = 800) -> List[str]:
    validated = []
    for chunk in chunks:
        length = len(chunk)
        if length < min_chars:
            if validated:
                validated[-1] += chunk
            else:
                print(f"警告：首块长度 {length} 过短，仍保留")
                validated.append(chunk)
        elif length > max_chars:
            print(f"警告：块长度 {length} 超过建议最大值 {max_chars}")
            validated.append(chunk)
        else:
            validated.append(chunk)
    return validated

def read_text_file(filepath: str) -> str:
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def add_to_rag(chunks: List[str], api_url: str, timestamp: Optional[int] = None) -> bool:
    try:
        payload = {"chunks": chunks}
        if timestamp is not None:
            metadata = [{"timestamp": timestamp, "tags": []} for _ in chunks]
            payload["metadata"] = metadata

        resp = requests.post(api_url, json=payload, timeout=60)
        if resp.status_code == 200:
            print(f"✅ 成功添加 {len(chunks)} 个块到RAG")
            print(f"   响应: {resp.json()}")
            return True
        else:
            print(f"❌ 添加失败，HTTP {resp.status_code}")
            print(resp.text)
            return False
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

def print_chunks_preview(chunks: List[str], preview_count: int = 5):
    print(f"\n📄 共生成 {len(chunks)} 个块，预览前 {preview_count} 个：")
    for i, chunk in enumerate(chunks[:preview_count]):
        print(f"\n--- 块{i+1} (长度{len(chunk)}) ---")
        print(chunk[:150] + ("..." if len(chunk) > 150 else ""))

def batch_add_to_rag(chunks: List[str], api_url: str, batch_size: int = 200, timestamp: Optional[int] = None):
    total = len(chunks)
    for i in range(0, total, batch_size):
        batch = chunks[i:i+batch_size]
        print(f"正在发送第 {i//batch_size + 1} 批，共 {len(batch)} 个块（已发送 {i} / {total}）...")
        if not add_to_rag(batch, api_url, timestamp):
            print("❌ 添加失败，停止发送")
            return False
    print(f"✅ 所有 {total} 个块已成功添加")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="中文智能分块工具")
    parser.add_argument("input_file", help="输入的文本文件路径（UTF-8编码）")
    parser.add_argument("--target-size", type=int, default=250,
                        help="目标块大小（字符数），默认250")
    parser.add_argument("--overlap", type=int, default=1,
                        help="重叠句子数，默认1")
    parser.add_argument("--min-size", type=int, default=50,
                        help="最小块大小，小于此值的块会被合并，默认50")
    parser.add_argument("--add", action="store_true",
                        help="分块后自动添加到RAG API")
    parser.add_argument("--api-url", default="http://127.0.0.1:8003/add_document",
                        help="RAG API地址")
    parser.add_argument("--mode", choices=["normal", "parent-child"], default="normal",
                        help="分块模式")
    parser.add_argument("--parent-size", type=int, default=600,
                        help="父块大小（仅 parent-child 模式）")
    parser.add_argument("--batch-size", type=int, default=500,
                        help="每批发送的块数（默认500）")
    parser.add_argument("--timestamp", type=int, default=0,
                        help="为所有块设置统一的时间戳（用于X轴），可为负数（如 -10000）")
    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        print(f"❌ 文件不存在: {args.input_file}")
        sys.exit(1)

    print(f"正在读取文件: {args.input_file}")
    text = read_text_file(args.input_file)
    print(f"文件总字符数: {len(text)}")
    print(f"将使用API地址: {args.api_url}")

    if args.mode == "parent-child":
        sub, parent = generate_parent_child_chunks(
            text,
            child_chars=args.target_size,
            parent_chars=args.parent_size,
            overlap_sentences=args.overlap
        )
        print(f"\n📦 生成子块 {len(sub)} 个，父块 {len(parent)} 个")
        print_chunks_preview(sub, 3)
        print("\n" + "="*50)
        print_chunks_preview(parent, 3)
        if args.add:
            print("\n正在添加子块到RAG...")
            batch_add_to_rag(sub, args.api_url, args.batch_size, args.timestamp)
    else:
        chunks = recursive_chunk_by_sentences(
            text,
            target_chars=args.target_size,
            overlap_sentences=args.overlap,
            min_chunk_chars=args.min_size
        )
        chunks = validate_chunks(chunks, min_chars=args.min_size)
        print_chunks_preview(chunks)
        if args.add:
            print("\n正在发送到RAG...")
            batch_add_to_rag(chunks, args.api_url, args.batch_size, args.timestamp)
        else:
            print("\n未添加 --add 标志，不发送到RAG。如需自动添加，请加上 --add 参数。")