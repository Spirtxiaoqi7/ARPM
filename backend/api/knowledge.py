"""
知识库管理 API 路由 (v4 - 移除手动加权)
"""
import os
import json
from flask import Blueprint, request, jsonify
from datetime import datetime

from core.retriever import retriever
from storage.vector_store import vector_store
from utils.chunker import Chunker
from config import ChunkConfig

knowledge_bp = Blueprint('knowledge', __name__)
chunker = Chunker()

# 分块上传会话存储（内存临时存储，生产环境应使用Redis或数据库）
upload_sessions = {}

@knowledge_bp.route('/api/knowledge', methods=['GET', 'POST', 'DELETE'])
def manage_knowledge():
    """知识库管理入口"""
    if request.method == 'GET':
        return _list_knowledge()
    elif request.method == 'POST':
        return _add_knowledge()
    else:
        return _delete_knowledge()

def _list_knowledge():
    """获取知识库列表"""
    try:
        chunks = vector_store.knowledge_chunks
        result = []
        for i, chunk in enumerate(chunks[:100]):  # 限制返回数量
            result.append({
                'index': i,
                'chunk_id': chunk.get('chunk_id'),
                'text': chunk.get('text', '')[:200] + '...' if len(chunk.get('text', '')) > 200 else chunk.get('text', ''),
                'source': chunk.get('source', 'unknown'),
                'timestamp': chunk.get('timestamp', {}),
                'child_count': len(chunk.get('children', []))
            })
        
        return jsonify({
            'total': len(chunks),
            'chunks': result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def _add_knowledge():
    """添加知识（文件上传）- 保持向后兼容的单文件上传"""
    if 'file' not in request.files:
        return jsonify({'error': '无文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    
    try:
        content = file.read().decode('utf-8')
        if not content.strip():
            return jsonify({'error': '文件为空'}), 400

        raw_chunk_config = request.form.get('chunk_config')
        chunk_config = {
            'child_size': ChunkConfig.CHILD_SIZE,
            'parent_size': ChunkConfig.PARENT_SIZE,
            'overlap_sentences': ChunkConfig.OVERLAP_SENTENCES
        }
        if raw_chunk_config:
            try:
                parsed = json.loads(raw_chunk_config)
                chunk_config = {
                    'child_size': max(50, min(1000, int(parsed.get('child_size', ChunkConfig.CHILD_SIZE)))),
                    'parent_size': max(100, min(3000, int(parsed.get('parent_size', ChunkConfig.PARENT_SIZE)))),
                    'overlap_sentences': max(0, min(10, int(parsed.get('overlap_sentences', ChunkConfig.OVERLAP_SENTENCES))))
                }
            except Exception:
                return jsonify({'error': 'chunk_config 格式错误'}), 400

        local_chunker = Chunker(
            child_size=chunk_config['child_size'],
            parent_size=chunk_config['parent_size'],
            overlap=chunk_config['overlap_sentences']
        )
        
        # 分块
        timestamp = {
            "round_num": 1,
            "physical_time": datetime.now().isoformat()
        }
        
        chunks = local_chunker.create_knowledge_chunks(
            content,
            source=file.filename,
            timestamp=timestamp
        )
        
        if not chunks:
            return jsonify({'error': '无有效内容'}), 400
        
        # 添加到向量库
        chunk_ids = retriever.add_knowledge(chunks)
        
        return jsonify({
            'success': True,
            'count': len(chunk_ids),
            'chunk_ids': chunk_ids,
            'chunk_config': chunk_config
        })
        
    except UnicodeDecodeError:
        return jsonify({'error': '编码错误，请使用UTF-8'}), 400
    except Exception as e:
        return jsonify({'error': f'处理失败: {str(e)}'}), 500


@knowledge_bp.route('/api/knowledge/chunk-config/default', methods=['GET'])
def get_default_chunk_config():
    """返回默认分块参数，供前端初始化展示。"""
    return jsonify({
        'child_size': ChunkConfig.CHILD_SIZE,
        'parent_size': ChunkConfig.PARENT_SIZE,
        'overlap_sentences': ChunkConfig.OVERLAP_SENTENCES
    })

def _delete_knowledge():
    """删除知识块（按索引）- 已废弃，建议使用 chunk_id 删除"""
    idx = request.args.get('index', type=int)
    if idx is None:
        return jsonify({'error': '缺少索引'}), 400
    
    try:
        # 从列表中移除
        if 0 <= idx < len(vector_store.knowledge_chunks):
            chunk_id = vector_store.knowledge_chunks[idx].get('chunk_id')
            success = vector_store.delete_knowledge_chunk(chunk_id)
            if success:
                retriever._build_bm25_index()
                return jsonify({'success': True, 'message': '已删除并重建索引'})
            return jsonify({'error': '删除失败'}), 500
        else:
            return jsonify({'error': '索引无效'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@knowledge_bp.route('/api/knowledge/clear', methods=['POST'])
def clear_knowledge():
    """
    一键清空知识库
    
    请求体:
    {
        "confirm": true  // 确认清空
    }
    """
    data = request.get_json() or {}
    if not data.get('confirm'):
        return jsonify({'error': '请设置 confirm: true 确认清空'}), 400
    
    try:
        success = vector_store.clear_knowledge_store()
        if success:
            # 同时重建 BM25 索引
            retriever._build_bm25_index()
            return jsonify({
                'success': True,
                'message': '知识库已清空',
                'files_deleted': ['metadata.json', 'faiss.index']
            })
        else:
            return jsonify({'error': '清空失败'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@knowledge_bp.route('/api/knowledge/search', methods=['POST'])
def search_knowledge():
    """RAG检索知识库"""
    data = request.get_json() or {}
    query = data.get('query', '').strip()
    top_k = min(max(data.get('top_k', 10), 1), 50)
    
    if not query:
        return jsonify({'error': '查询不能为空'}), 400
    
    try:
        results = vector_store.search_knowledge(query, k=top_k)
        return jsonify({
            'query': query,
            'total': len(results),
            'results': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@knowledge_bp.route('/api/knowledge/stats', methods=['GET'])
def knowledge_stats():
    """知识库统计"""
    return jsonify(retriever.get_stats())


@knowledge_bp.route('/api/knowledge/chunk/<chunk_id>', methods=['DELETE'])
def delete_knowledge_chunk(chunk_id):
    """按chunk_id删除知识库块（在线删除）"""
    try:
        success = vector_store.delete_knowledge_chunk(chunk_id)
        if success:
            # 同时重建BM25索引
            retriever._build_bm25_index()
            return jsonify({'success': True, 'message': f'已删除块 {chunk_id}'})
        else:
            return jsonify({'error': '块不存在'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@knowledge_bp.route('/api/knowledge/chunks', methods=['GET'])
def list_knowledge_chunks():
    """获取知识库块列表（用于自检模块）"""
    try:
        chunks = []
        for chunk in vector_store.knowledge_chunks:
            chunks.append({
                'chunk_id': chunk.get('chunk_id'),
                'text': chunk.get('text', '')[:200] + '...' if len(chunk.get('text', '')) > 200 else chunk.get('text', ''),
                'source': chunk.get('source', 'unknown'),
                'timestamp': chunk.get('timestamp', {}),
                'child_count': len(chunk.get('children', []))
            })
        return jsonify({
            'total': len(chunks),
            'chunks': chunks
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@knowledge_bp.route('/api/upload_batch', methods=['POST'])
def upload_batch():
    """批量上传（用于前端分块上传）"""
    data = request.get_json() or {}
    chunks = data.get('chunks', [])
    
    if not chunks:
        return jsonify({'error': '无数据'}), 400
    
    if len(chunks) > 1000:
        return jsonify({'error': '单次超过1000个块'}), 400
    
    try:
        # 添加时间戳
        for chunk in chunks:
            if 'metadata' not in chunk:
                chunk['metadata'] = {}
            if 'timestamp' not in chunk['metadata']:
                chunk['metadata']['timestamp'] = {
                    "round_num": 1,
                    "physical_time": datetime.now().isoformat()
                }
        
        chunk_ids = retriever.add_knowledge(chunks)
        return jsonify({'success': True, 'count': len(chunk_ids)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@knowledge_bp.route('/api/knowledge/upload/init', methods=['POST'])
def init_chunked_upload():
    """初始化分块上传会话"""
    data = request.get_json() or {}
    filename = data.get('filename', 'unknown')
    total_chunks = data.get('total_chunks', 0)
    
    session_id = f"upload_{datetime.now().timestamp()}_{filename}"
    upload_sessions[session_id] = {
        'filename': filename,
        'total_chunks': total_chunks,
        'received_chunks': 0,
        'chunks': [],
        'created_at': datetime.now().isoformat()
    }
    
    return jsonify({
        'success': True,
        'session_id': session_id,
        'message': '上传会话已创建'
    })


@knowledge_bp.route('/api/knowledge/upload/chunk', methods=['POST'])
def upload_chunk():
    """接收分块数据"""
    data = request.get_json() or {}
    session_id = data.get('session_id')
    chunks = data.get('chunks', [])
    batch_index = data.get('batch_index', 0)
    is_last = data.get('is_last', False)
    
    if not session_id or session_id not in upload_sessions:
        return jsonify({'error': '无效的上传会话'}), 400
    
    if not chunks:
        return jsonify({'error': '无数据块'}), 400
    
    try:
        session = upload_sessions[session_id]
        
        # 添加时间戳到每个块
        for chunk in chunks:
            if 'metadata' not in chunk:
                chunk['metadata'] = {}
            if 'timestamp' not in chunk['metadata']:
                chunk['metadata']['timestamp'] = {
                    "round_num": 1,
                    "physical_time": datetime.now().isoformat()
                }
        
        # 处理当前批次（每100块）
        chunk_ids = retriever.add_knowledge(chunks)
        session['chunks'].extend(chunk_ids)
        session['received_chunks'] += len(chunks)
        
        # 计算进度
        progress = 0
        if session['total_chunks'] > 0:
            progress = min(100, int(session['received_chunks'] / session['total_chunks'] * 100))
        
        # 如果是最后一批，清理会话
        if is_last:
            final_count = session['received_chunks']
            del upload_sessions[session_id]
            return jsonify({
                'success': True,
                'completed': True,
                'count': final_count,
                'progress': 100,
                'message': f'上传完成，共 {final_count} 个片段'
            })
        
        return jsonify({
            'success': True,
            'completed': False,
            'received': session['received_chunks'],
            'total': session['total_chunks'],
            'progress': progress,
            'batch_index': batch_index,
            'message': f'已接收 {session["received_chunks"]}/{session["total_chunks"]} 个片段'
        })
        
    except Exception as e:
        return jsonify({'error': f'处理失败: {str(e)}'}), 500


@knowledge_bp.route('/api/knowledge/upload/cancel', methods=['POST'])
def cancel_chunked_upload():
    """取消分块上传"""
    data = request.get_json() or {}
    session_id = data.get('session_id')
    
    if session_id and session_id in upload_sessions:
        del upload_sessions[session_id]
        return jsonify({'success': True, 'message': '上传已取消'})
    
    return jsonify({'success': False, 'message': '会话不存在'})
