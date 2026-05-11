"""
会话管理 API 路由 - 多会话隔离版本
- 每个会话有独立的角色配置
- 删除会话时同步删除对应的向量索引
"""
import os
import glob
from flask import Blueprint, request, jsonify

from storage.memory_store import memory_store
from storage.vector_store import vector_store
from config import MEMORY_DB_PATH, VECTOR_DB_PATH, FlaskConfig, LLMConfig

session_bp = Blueprint('session', __name__)


@session_bp.route('/api/ui/state', methods=['GET'])
def get_ui_state():
    """Frontend-facing state for the open-source showcase UI."""
    try:
        sessions = memory_store.get_all_sessions()
        knowledge_stats = vector_store.get_knowledge_stats()
        chat_stats = vector_store.get_chat_stats()
        return jsonify({
            'app': {
                'name': 'ARPM-v4',
                'port': FlaskConfig.PORT,
                'debug': FlaskConfig.DEBUG,
                'default_model': LLMConfig.DEFAULT_MODEL,
                'default_base_url': LLMConfig.DEFAULT_BASE_URL
            },
            'stats': {
                'session_count': len(sessions),
                'knowledge_chunks': knowledge_stats.get('total_chunks', 0),
                'knowledge_vectors': knowledge_stats.get('total_vectors', 0),
                'chat_sessions': chat_stats.get('total_sessions', 0),
                'chat_vectors': chat_stats.get('total_vectors', 0)
            },
            'features': {
                'knowledge_search': True,
                'session_memory': True,
                'diagnostics': True,
                'export_current_session': True,
                'split_settings': True
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@session_bp.route('/api/sessions', methods=['GET'])
def list_sessions():
    """获取会话列表（包含角色配置信息）"""
    try:
        sessions = memory_store.get_all_sessions()
        # 为每个会话添加角色配置信息
        for session in sessions:
            session_id = session.get('id')
            if session_id:
                session_data = memory_store.load_session(session_id)
                config = session_data.get('config', {})
                session['session_id'] = session_id
                session['character_name'] = config.get('character_name', 'AI助手')
                session['user_name'] = config.get('user_name', '用户')
        return jsonify(sessions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@session_bp.route('/api/session/<session_id>', methods=['GET', 'DELETE'])
def manage_session(session_id):
    """获取或删除会话"""
    if request.method == 'GET':
        try:
            data = memory_store.load_session(session_id)
            # 确保返回配置信息
            if 'config' not in data:
                data['config'] = {
                    'user_name': '用户',
                    'user_persona': '',
                    'character_name': 'AI助手',
                    'system_prompt': ''
                }
            return jsonify(data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        # DELETE - 删除会话时同步删除向量索引
        try:
            # 1. 删除会话数据
            memory_store.delete_session(session_id)
            # 2. 删除该会话的向量索引（隔离版本）
            vector_store.delete_chat_session(session_id)
            return jsonify({
                'success': True,
                'message': f'会话 {session_id} 及其向量索引已删除'
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@session_bp.route('/api/history', methods=['POST'])
def save_history():
    """保存对话历史"""
    data = request.get_json() or {}
    session_id = data.get('session_id')
    messages = data.get('messages', [])
    
    if not session_id:
        return jsonify({'error': '缺少会话ID'}), 400
    
    try:
        session_data = memory_store.load_session(session_id)
        session_data['messages'] = messages
        if messages:
            session_data['last_round'] = max((m.get('round', 0) for m in messages), default=0)
        else:
            session_data['last_round'] = 0
            session_data['memories'] = []
        
        # 如果没有名称，生成一个
        if not session_data.get('session_name'):
            session_data['session_name'] = memory_store.generate_session_name()
        
        memory_store.save_session(session_id, session_data)
        return jsonify({
            'success': True, 
            'session_name': session_data['session_name'],
            'config': session_data.get('config', {})
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@session_bp.route('/api/history/<session_id>', methods=['GET'])
def get_history(session_id):
    """获取对话历史和角色配置"""
    try:
        data = memory_store.load_session(session_id)
        return jsonify({
            'session_id': session_id,
            'session_name': data.get('session_name', session_id),
            'messages': data.get('messages', []),
            'last_round': data.get('last_round', 0),
            'memories': data.get('memories', []),
            'config': data.get('config', {
                'user_name': '用户',
                'user_persona': '',
                'character_name': 'AI助手',
                'system_prompt': ''
            })
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== 对话历史块管理（多会话隔离）====================

@session_bp.route('/api/session/<session_id>/chat_index', methods=['DELETE'])
def clear_session_chat_index(session_id):
    """清空指定会话的对话历史索引（保留会话元数据）"""
    try:
        success = vector_store.delete_chat_session(session_id)
        if success:
            return jsonify({
                'success': True,
                'message': f'会话 {session_id} 的对话索引已清空'
            })
        else:
            return jsonify({
                'success': False,
                'message': '没有找到该会话的索引或清空失败'
            }), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@session_bp.route('/api/chat/chunks', methods=['GET'])
def list_all_chat_chunks():
    """获取所有会话的对话历史块（用于自检模块）"""
    try:
        # 获取所有有对话数据的session
        session_ids = vector_store.get_all_session_ids()
        all_chunks = []
        
        for session_id in session_ids:
            chunks = vector_store.get_chat_chunks_by_session(session_id)
            for chunk in chunks:
                all_chunks.append({
                    'chunk_id': chunk.get('chunk_id'),
                    'text': chunk.get('text', '')[:100] + '...' if len(chunk.get('text', '')) > 100 else chunk.get('text', ''),
                    'session_id': session_id,
                    'user_name': chunk.get('user_name'),
                    'character_name': chunk.get('character_name'),
                    'timestamp': chunk.get('timestamp', {}),
                    'source_type': 'chat'
                })
        
        return jsonify({
            'total_sessions': len(session_ids),
            'total': len(all_chunks),
            'total_chunks': len(all_chunks),
            'chunks': all_chunks
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@session_bp.route('/api/chat/chunks/<session_id>', methods=['GET'])
def list_session_chat_chunks(session_id):
    """获取指定会话的对话历史块"""
    try:
        chunks = vector_store.get_chat_chunks_by_session(session_id)
        result = []
        for chunk in chunks:
            result.append({
                'chunk_id': chunk.get('chunk_id'),
                'text': chunk.get('text', '')[:100] + '...' if len(chunk.get('text', '')) > 100 else chunk.get('text', ''),
                'user_name': chunk.get('user_name'),
                'character_name': chunk.get('character_name'),
                'timestamp': chunk.get('timestamp', {})
            })
        return jsonify({
            'session_id': session_id,
            'total': len(result),
            'chunks': result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@session_bp.route('/api/chat/chunk/<chunk_id>', methods=['DELETE'])
def delete_chat_chunk(chunk_id):
    """
    按chunk_id删除对话历史块
    注意：在多会话隔离架构下，需要遍历所有session查找
    """
    try:
        # 获取所有session，逐个查找并删除
        session_ids = vector_store.get_all_session_ids()
        deleted = False
        
        for session_id in session_ids:
            chunks = vector_store._get_session_chunks(session_id)
            for i, chunk in enumerate(chunks):
                if chunk.get('chunk_id') == chunk_id:
                    # 找到并删除
                    chunks.pop(i)
                    # 重建索引
                    vector_store._rebuild_session_index(session_id)
                    # 保存
                    vector_store._save_session_store(session_id)
                    deleted = True
                    break
            if deleted:
                break
        
        if deleted:
            return jsonify({'success': True, 'message': f'已删除对话块 {chunk_id}'})
        else:
            return jsonify({'error': '块不存在'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== 一键清除所有数据 ====================

@session_bp.route('/api/data/clear_all', methods=['POST'])
def clear_all_data():
    """
    一键清除所有数据（知识库 + 所有会话对话历史 + 会话）
    """
    data = request.get_json() or {}
    
    if not data.get('confirm'):
        return jsonify({'error': '请设置 confirm: true 确认清空'}), 400
    
    results = {
        'knowledge_cleared': False,
        'chat_sessions_cleared': [],
        'sessions_cleared': False,
        'errors': []
    }
    
    try:
        # 1. 清空知识库
        if data.get('clear_kb', True):
            try:
                # 删除知识库文件
                results['knowledge_cleared'] = vector_store.clear_knowledge_store()
                # 重新加载知识库（会创建空索引）
                from core.retriever import retriever
                retriever._build_bm25_index()
            except Exception as e:
                results['errors'].append(f'知识库清空失败: {str(e)}')
        
        # 2. 清空所有会话的对话历史
        if data.get('clear_chat', True):
            try:
                session_ids = vector_store.get_all_session_ids()
                for session_id in session_ids:
                    success = vector_store.delete_chat_session(session_id)
                    if success:
                        results['chat_sessions_cleared'].append(session_id)
            except Exception as e:
                results['errors'].append(f'对话历史清空失败: {str(e)}')
        
        # 3. 清空所有会话
        if data.get('clear_sessions', True):
            try:
                session_files = glob.glob(os.path.join(MEMORY_DB_PATH, 'session_*.json'))
                for f in session_files:
                    os.remove(f)
                results['sessions_cleared'] = True
                results['sessions_deleted'] = len(session_files)
            except Exception as e:
                results['errors'].append(f'会话清空失败: {str(e)}')
        
        # 判断是否全部成功
        all_success = (
            (not data.get('clear_kb', True) or results['knowledge_cleared']) and
            (not data.get('clear_chat', True) or not results['errors']) and
            (not data.get('clear_sessions', True) or results['sessions_cleared'])
        )
        
        if all_success:
            return jsonify({
                'success': True,
                'message': '所有数据已清空',
                'details': results
            })
        else:
            return jsonify({
                'success': False,
                'message': '部分数据清空失败',
                'details': results
            }), 500
            
    except Exception as e:
        return jsonify({'error': f'清空失败: {str(e)}'}), 500


@session_bp.route('/api/data/stats', methods=['GET'])
def get_data_stats():
    """获取数据存储统计（多会话隔离版本）"""
    try:
        # 统计会话文件
        session_files = glob.glob(os.path.join(MEMORY_DB_PATH, 'session_*.json'))
        
        # 统计知识库文件
        kb_files = {
            'metadata': os.path.exists(os.path.join(VECTOR_DB_PATH, 'knowledge', 'metadata.json')),
            'index': os.path.exists(os.path.join(VECTOR_DB_PATH, 'knowledge', 'faiss.index'))
        }
        
        # 统计对话历史（多会话）
        chat_sessions = vector_store.get_all_session_ids()
        session_stats = {}
        total_chat_vectors = 0
        
        for session_id in chat_sessions:
            stats = vector_store.get_session_stats(session_id)
            session_stats[session_id] = stats
            total_chat_vectors += stats.get('vectors', 0)
        
        return jsonify({
            'memory': {
                'session_count': len(session_files),
                'session_files': [os.path.basename(f) for f in session_files[:5]]
            },
            'vector_db': {
                'knowledge': {
                    'chunks_in_memory': len(vector_store.knowledge_chunks),
                    'vectors_in_memory': vector_store.knowledge_index.ntotal if vector_store.knowledge_index else 0,
                    'files_exist': kb_files
                },
                'chat': {
                    'session_count': len(chat_sessions),
                    'session_ids': chat_sessions[:5],  # 最多显示5个
                    'total_vectors': total_chat_vectors,
                    'session_details': session_stats
                }
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
