"""
Chat API routes.
- Each session keeps its own character config.
- Chat history is isolated by session.
- Knowledge base is shared globally.
"""
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app

from core.retriever import retriever
from core.generator import generator
from core.memory_manager import memory_manager
from storage.memory_store import memory_store
from storage.vector_store import vector_store
from utils.time_utils import DualTimestamp
from utils.admin_logger import log_admin
from config import get_ablation_config, sanitize_tuning_config

chat_bp = Blueprint('chat', __name__)

# Session-scoped generation state used by cancellation.
# Structure: {session_id: {'cancelled': bool, 'timestamp': datetime}}
generation_states = {}


def _log_retrieval_details(label: str, chunks: list, limit: int = 5):
    """Print retrieved chunks with score and weight details for debugging."""
    for idx, chunk in enumerate((chunks or [])[:limit], 1):
        text = (chunk.get('text') or '').replace('\n', ' ').strip()
        text = text[:120] + ('...' if len(text) > 120 else '')
        ts = chunk.get('timestamp', {})
        print(
            f"[Retrieve][{label}][{idx}] "
            f"round={ts.get('round_num', '-')} "
            f"physical_time={ts.get('physical_time', '')} "
            f"score={chunk.get('score', 0):.3f} "
            f"semantic={chunk.get('semantic_score', chunk.get('score', 0)):.3f} "
            f"weighted={chunk.get('weighted_score', chunk.get('score', 0)):.3f} "
            f"temporal={chunk.get('temporal_weight', 1.0):.3f} "
            f"role_boost={chunk.get('role_weight_boost', chunk.get('kb_role_weight_boost', 0)):.3f} "
            f"source={chunk.get('source', chunk.get('session_id', 'unknown'))} "
            f"text={text}"
        )


def _model_label(api_config: dict) -> str:
    return (api_config or {}).get('model') or 'unknown-model'


def _with_model_prefix(text: str, api_config: dict) -> str:
    return f"[model={_model_label(api_config)}] {text or ''}"


def get_session_config(session_id: str) -> dict:
    """Get the session-scoped character configuration, creating defaults if needed."""
    session_data = memory_store.load_session(session_id)
    
    # Create default character config for new sessions.
    if 'config' not in session_data:
        session_data['config'] = {
            'user_name': '用户',
            'user_persona': '',
            'character_name': 'AI助手',
            'system_prompt': '',
            'tuning_config': sanitize_tuning_config(),
            'protocol_config': {
                'protocol_mode': 'auto',
                'reasoning_model_mode': 'auto',
                'auto_repair_response': True,
                'diagnostic_mode': True
            },
            'chunk_config': {
                'child_size': 200,
                'parent_size': 600,
                'overlap_sentences': 1
            }
        }
        memory_store.save_session(session_id, session_data)
    else:
        session_data['config']['tuning_config'] = sanitize_tuning_config(session_data['config'].get('tuning_config'))
        protocol_config = session_data['config'].get('protocol_config', {})
        session_data['config']['protocol_config'] = {
            'protocol_mode': protocol_config.get('protocol_mode', 'auto'),
            'reasoning_model_mode': protocol_config.get('reasoning_model_mode', 'auto'),
            'auto_repair_response': bool(protocol_config.get('auto_repair_response', True)),
            'diagnostic_mode': bool(protocol_config.get('diagnostic_mode', True))
        }
        chunk_config = session_data['config'].get('chunk_config', {})
        session_data['config']['chunk_config'] = {
            'child_size': max(50, min(1000, int(chunk_config.get('child_size', 200)))),
            'parent_size': max(100, min(3000, int(chunk_config.get('parent_size', 600)))),
            'overlap_sentences': max(0, min(10, int(chunk_config.get('overlap_sentences', 1))))
        }
        memory_store.save_session(session_id, session_data)
    
    return session_data['config']


def save_session_config(session_id: str, config: dict):
    """Save the session-scoped character configuration."""
    session_data = memory_store.load_session(session_id)
    session_data['config'] = config
    memory_store.save_session(session_id, session_data)


@chat_bp.route('/api/chat/config', methods=['GET'])
def get_chat_config():
    """Return the config for a specific session."""
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({'error': '缺少 session_id 参数'}), 400
    
    config = get_session_config(session_id)
    return jsonify({
        'session_id': session_id,
        'config': config
    })


@chat_bp.route('/api/chat/config', methods=['POST'])
def save_chat_config():
    """Persist the config for a specific session."""
    data = request.get_json() or {}
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({'error': '缺少 session_id 参数'}), 400
    
    config = {
        'user_name': data.get('user_name', '用户'),
        'user_persona': data.get('user_persona', ''),
        'character_name': data.get('character_name', 'AI助手'),
        'system_prompt': data.get('system_prompt', ''),
        'tuning_config': sanitize_tuning_config(data.get('tuning_config')),
        'protocol_config': {
            'protocol_mode': (data.get('protocol_config') or {}).get('protocol_mode', 'auto'),
            'reasoning_model_mode': (data.get('protocol_config') or {}).get('reasoning_model_mode', 'auto'),
            'auto_repair_response': bool((data.get('protocol_config') or {}).get('auto_repair_response', True)),
            'diagnostic_mode': bool((data.get('protocol_config') or {}).get('diagnostic_mode', True))
        },
        'chunk_config': {
            'child_size': max(50, min(1000, int((data.get('chunk_config') or {}).get('child_size', 200)))),
            'parent_size': max(100, min(3000, int((data.get('chunk_config') or {}).get('parent_size', 600)))),
            'overlap_sentences': max(0, min(10, int((data.get('chunk_config') or {}).get('overlap_sentences', 1))))
        }
    }
    
    save_session_config(session_id, config)
    return jsonify({'success': True, 'config': config})


@chat_bp.route('/api/chat', methods=['POST'])
def handle_chat():
    """Handle a chat request for the current session."""
    data = request.get_json() or {}
    
    # Extract and validate input payload.
    user_input = data.get('message', '').strip()
    if not user_input:
        return jsonify({'error': '消息不能为空'}), 400
    
    if len(user_input) > 10000:
        return jsonify({'error': '消息过长'}), 400
    
    session_id = data.get('session_id') or str(uuid.uuid4())
    current_round = data.get('round', 1)
    api_config = data.get('api_config', {})
    
    # 获取会话角色配置；新会话会自动创建默认配置。
    session_config = get_session_config(session_id)
    
    # 前端如传入新配置，则更新并保存。
    user_name = data.get('user_name')
    user_persona = data.get('user_persona')
    character_name = data.get('character_name')
    system_prompt = data.get('system_prompt')
    tuning_config = data.get('tuning_config')
    protocol_config = data.get('protocol_config')
    chunk_config = data.get('chunk_config')
    
    # 按需更新配置字段。
    if user_name is not None:
        session_config['user_name'] = user_name
    if user_persona is not None:
        session_config['user_persona'] = user_persona
    if character_name is not None:
        session_config['character_name'] = character_name
    if system_prompt is not None:
        session_config['system_prompt'] = system_prompt
    if tuning_config is not None:
        session_config['tuning_config'] = sanitize_tuning_config(tuning_config)
    if protocol_config is not None:
        session_config['protocol_config'] = {
            'protocol_mode': protocol_config.get('protocol_mode', 'auto'),
            'reasoning_model_mode': protocol_config.get('reasoning_model_mode', 'auto'),
            'auto_repair_response': bool(protocol_config.get('auto_repair_response', True)),
            'diagnostic_mode': bool(protocol_config.get('diagnostic_mode', True))
        }
    if chunk_config is not None:
        session_config['chunk_config'] = {
            'child_size': max(50, min(1000, int(chunk_config.get('child_size', 200)))),
            'parent_size': max(100, min(3000, int(chunk_config.get('parent_size', 600)))),
            'overlap_sentences': max(0, min(10, int(chunk_config.get('overlap_sentences', 1))))
        }
    
    # 淇濆瓨鏇存柊鍚庣殑閰嶇疆
    save_session_config(session_id, session_config)
    
    # 浣跨敤鏈€缁堥厤缃?
    user_name = session_config['user_name']
    user_persona = session_config['user_persona']
    character_name = session_config['character_name']
    system_prompt = session_config['system_prompt']
    tuning_config = sanitize_tuning_config(session_config.get('tuning_config'))
    protocol_config = session_config.get('protocol_config', {})
    
    # 鑾峰彇娑堣瀺瀹為獙閰嶇疆
    raw_ablation = data.get('ablation_config', {})
    ablation_config = get_ablation_config(
        rag_enabled=raw_ablation.get('rag_enabled', True),
        kb_enabled=raw_ablation.get('kb_enabled', True),
        chat_enabled=raw_ablation.get('chat_enabled', True),
        temporal_enabled=raw_ablation.get('temporal_enabled', True),
        bm25_enabled=raw_ablation.get('bm25_enabled', True),
        disambiguation_enabled=False,  # 已禁用
        regeneration_enabled=raw_ablation.get('regeneration_enabled', True),
        regen_regex=raw_ablation.get('regen_regex', True),
        regen_semantic=raw_ablation.get('regen_semantic', False),
        regen_max_attempts=raw_ablation.get('regen_max_attempts', 1)
    )
    
    # 获取相似度阈值。
    similarity_threshold = data.get('similarity_threshold')
    if similarity_threshold is not None:
        similarity_threshold = max(0.0, min(1.0, float(similarity_threshold)))
    
    # 初始化生成状态，用于取消检测。
    generation_states[session_id] = {
        'cancelled': False,
        'timestamp': datetime.now()
    }
    
    try:
        print(f"[Chat] Processing request for session {session_id}, round {current_round}")
        
        # 检查是否已取消。
        if generation_states.get(session_id, {}).get('cancelled'):
            return jsonify({'error': 'generation cancelled', 'cancelled': True}), 499
        
        # 第一层：检索角色感知上下文。
        print(f"[Chat] Retrieving context for session {session_id}")
        rag_context = retriever.retrieve(
            query=user_input,
            session_id=session_id,
            current_round=current_round,
            ablation_config=ablation_config,
            user_name=user_name,
            character_name=character_name,
            similarity_threshold=similarity_threshold,
            tuning_config=tuning_config
        )
        print(f"[Chat] Retrieved: {len(rag_context['knowledge'])} knowledge, {len(rag_context['chat_history'])} chat history")
        
        # 搴旂敤鏃舵€佹潈閲?
        temporal_enabled = ablation_config.get('temporal_enabled', True)
        if rag_context['knowledge']:
            rag_context['knowledge'] = memory_manager.apply_weights_to_results(
                rag_context['knowledge'],
                current_round,
                temporal_enabled=temporal_enabled,
                tuning_config=tuning_config
            )
        if rag_context['chat_history']:
            rag_context['chat_history'] = memory_manager.apply_weights_to_results(
                rag_context['chat_history'],
                current_round,
                temporal_enabled=temporal_enabled,
                tuning_config=tuning_config
            )
        _log_retrieval_details('knowledge', rag_context.get('knowledge', []))
        _log_retrieval_details('chat', rag_context.get('chat_history', []))
        
        # 检查是否已取消。
        if generation_states.get(session_id, {}).get('cancelled'):
            return jsonify({'error': 'generation cancelled', 'cancelled': True}), 499
        
        # 第二层：生成回复。
        session_data = memory_store.load_session(session_id)
        history = session_data.get('messages', [])[-10:]
        regen_config = ablation_config.get('regeneration', {})
        
        result = generator.generate(
            user_input=user_input,
            rag_context=rag_context,
            current_round=current_round,
            api_config=api_config,
            system_prompt=system_prompt,
            user_name=user_name,
            user_persona=user_persona,
            character_name=character_name,
            disambiguation_enabled=False,  # 已禁用
            regeneration_config=regen_config,
            history=history,
            tuning_config=tuning_config,
            protocol_config=protocol_config
        )
        
        # 检查是否已取消。
        if generation_states.get(session_id, {}).get('cancelled'):
            return jsonify({'error': 'generation cancelled', 'cancelled': True}), 499
        
        # 保存到记忆，执行原子写入。
        physical_time = datetime.now().isoformat()
        combined_text = f"{user_name}: {user_input}\n{character_name}: {result['reply']}"
        log_admin("B", {
            "event": "dialog_turn",
            "session_id": session_id,
            "round": current_round,
            "physical_time": physical_time,
            "model": _model_label(api_config),
            "user_name": user_name,
            "character_name": character_name,
            "user_input": user_input,
            "user_input_with_model": _with_model_prefix(user_input, api_config),
            "assistant_reply": result.get('reply', ''),
            "assistant_reply_with_model": _with_model_prefix(result.get('reply', ''), api_config),
        })
        log_admin("C", {
            "event": "cot_analysis",
            "session_id": session_id,
            "round": current_round,
            "physical_time": physical_time,
            "model": _model_label(api_config),
            "analysis": result.get('analysis', ''),
            "regeneration_info": result.get('regeneration_info'),
            "protocol_info": result.get('protocol_info'),
        })
        
        chat_atom = {
            "text": combined_text,
            "user_name": user_name,
            "character_name": character_name,
            "user_input": user_input,
            "assistant_reply": result['reply'],
            "session_id": session_id,
            "timestamp": {"round_num": current_round, "physical_time": physical_time}
        }
        
        # 使用会话隔离接口保存到对应 session。
        vector_store.add_chat_atom(chat_atom, session_id=session_id)
        
        # 鏇存柊浼氳瘽鏁版嵁
        if 'last_round' not in session_data:
            session_data['last_round'] = 0
        session_data['last_round'] = current_round
        
        if 'messages' not in session_data:
            session_data['messages'] = []
        session_data['messages'].append({
            'role': 'user',
            'content': user_input,
            'timestamp': physical_time,
            'round': current_round
        })
        session_data['messages'].append({
            'role': 'assistant',
            'content': result['reply'],
            'timestamp': physical_time,
            'round': current_round
        })
        
        if 'memories' not in session_data:
            session_data['memories'] = []
        session_data['memories'].append({
            'round': current_round,
            'user': user_input,
            'assistant': result['reply'],
            'analysis': result.get('analysis', ''),
            'timestamp': physical_time
        })
        
        memory_store.save_session(session_id, session_data)
        
        # 鏍煎紡鍖栧彫鍥炲唴瀹癸紙鍖呭惈瀹屾暣鏉冮噸淇℃伅锛?
        knowledge_blocks = []
        for chunk in rag_context.get('knowledge', [])[:5]:
            knowledge_blocks.append({
                'text': chunk.get('text', '')[:300],
                'source': chunk.get('source', 'unknown'),
                'round_num': chunk.get('timestamp', {}).get('round_num', '-'),
                'physical_time': chunk.get('timestamp', {}).get('physical_time', '')[:16].replace('T', ' '),
                # 鏉冮噸淇℃伅
                # 权重信息
                'semantic_score': round(chunk.get('semantic_score', chunk.get('score', 0)), 3),
                'original_score': round(chunk.get('score', 0), 3),
                'weighted_score': round(chunk.get('weighted_score', chunk.get('score', 0)), 3),
                'temporal_weight': round(chunk.get('temporal_weight', 1.0), 3),
                'kb_role_weight_boost': round(chunk.get('kb_role_weight_boost', 0), 3)
            })
        
        chat_blocks = []
        for chunk in rag_context.get('chat_history', [])[:10]:
            chat_blocks.append({
                'text': chunk.get('text', '')[:200],
                'user_name': chunk.get('user_name', '用户'),
                'character_name': chunk.get('character_name', 'AI'),
                'user_input': chunk.get('user_input', ''),
                'assistant_reply': chunk.get('assistant_reply', ''),
                'round_num': chunk.get('timestamp', {}).get('round_num', '-'),
                'physical_time': chunk.get('timestamp', {}).get('physical_time', '')[:16].replace('T', ' '),
                # 权重信息
                'semantic_score': round(chunk.get('semantic_score', chunk.get('score', 0)), 3),
                'original_score': round(chunk.get('score', 0), 3),
                'weighted_score': round(chunk.get('weighted_score', chunk.get('score', 0)), 3),
                'temporal_weight': round(chunk.get('temporal_weight', 1.0), 3),
                'role_weight_boost': round(chunk.get('role_weight_boost', 0), 3)
            })
        
        return jsonify({
            'session_id': session_id,
            'round': current_round,
            'status': result['status'],
            'reply': result['reply'],
            'analysis': result.get('analysis', ''),
            'config': session_config,  # 返回当前会话配置，确保前后端同步。
            'rag_context': {
                'knowledge_count': len(rag_context['knowledge']),
                'chat_count': len(rag_context['chat_history']),
                'rag_enabled': rag_context.get('rag_enabled', True),
                'kb_enabled': rag_context.get('kb_enabled', True),
                'chat_enabled': rag_context.get('chat_enabled', True),
                'temporal_enabled': ablation_config.get('temporal_enabled', True),
                'knowledge_blocks': knowledge_blocks,
                'chat_blocks': chat_blocks
            },
            'regeneration_info': result.get('regeneration_info'),
            'protocol_info': result.get('protocol_info')
        })
        
    except Exception as e:
        print(f"[ERROR] Chat failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'生成失败: {str(e)}'}), 500
    finally:
        # Always clear generation state before exiting.
        if session_id in generation_states:
            del generation_states[session_id]


@chat_bp.route('/api/chat/cancel', methods=['POST'])
def cancel_generation():
    """Cancel generation for the specified session."""
    data = request.get_json() or {}
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({'error': '缺少 session_id'}), 400
    
    if session_id in generation_states:
        generation_states[session_id]['cancelled'] = True
        return jsonify({'success': True, 'message': 'cancel signal sent'})
    
    return jsonify({'success': False, 'message': '该会话当前没有正在进行的生成任务'}), 404


@chat_bp.route('/api/chat/regenerate', methods=['POST'])
def regenerate_message():
    """Regenerate the answer for a specific round."""
    data = request.get_json() or {}
    
    session_id = data.get('session_id')
    round_num = data.get('round')
    user_input = data.get('message', '').strip()
    
    if not session_id or round_num is None:
        return jsonify({'error': '缺少 session_id 或 round 参数'}), 400
    
    try:
        # 1. 删除该轮次的向量索引。
        deleted_chunks = vector_store.delete_chat_chunks_by_session_and_round(
            session_id, round_num
        )
        print(f"[Regenerate] Deleted {len(deleted_chunks)} chunks for session {session_id} round {round_num}")
        
        # 2. 获取该会话配置，确保角色隔离。
        session_config = get_session_config(session_id)
        
        api_config = data.get('api_config', {})
        similarity_threshold = data.get('similarity_threshold')
        tuning_config = sanitize_tuning_config(data.get('tuning_config') or session_config.get('tuning_config'))
        protocol_config = data.get('protocol_config') or session_config.get('protocol_config', {})
        if similarity_threshold is not None:
            similarity_threshold = max(0.0, min(1.0, float(similarity_threshold)))
        
        raw_ablation = data.get('ablation_config', {})
        ablation_config = get_ablation_config(
            rag_enabled=raw_ablation.get('rag_enabled', True),
            kb_enabled=raw_ablation.get('kb_enabled', True),
            chat_enabled=raw_ablation.get('chat_enabled', True),
            temporal_enabled=raw_ablation.get('temporal_enabled', True),
            bm25_enabled=raw_ablation.get('bm25_enabled', True),
            disambiguation_enabled=False,
            regeneration_enabled=raw_ablation.get('regeneration_enabled', True),
            regen_regex=raw_ablation.get('regen_regex', True),
            regen_semantic=raw_ablation.get('regen_semantic', False),
            regen_max_attempts=raw_ablation.get('regen_max_attempts', 1)
        )
        
        # 3. 重新检索，限定在当前 session。
        rag_context = retriever.retrieve(
            query=user_input,
            session_id=session_id,
            current_round=round_num,
            ablation_config=ablation_config,
            user_name=session_config['user_name'],
            character_name=session_config['character_name'],
            similarity_threshold=similarity_threshold,
            tuning_config=tuning_config
        )
        
        temporal_enabled = ablation_config.get('temporal_enabled', True)
        if rag_context['knowledge']:
            rag_context['knowledge'] = memory_manager.apply_weights_to_results(
                rag_context['knowledge'],
                round_num,
                temporal_enabled=temporal_enabled,
                tuning_config=tuning_config
            )
        if rag_context['chat_history']:
            rag_context['chat_history'] = memory_manager.apply_weights_to_results(
                rag_context['chat_history'],
                round_num,
                temporal_enabled=temporal_enabled,
                tuning_config=tuning_config
            )
        _log_retrieval_details('knowledge-regen', rag_context.get('knowledge', []))
        _log_retrieval_details('chat-regen', rag_context.get('chat_history', []))
        
        # 4. 閲嶆柊鐢熸垚锛堜娇鐢ㄤ細璇濋殧绂荤殑瑙掕壊閰嶇疆锛?
        session_data = memory_store.load_session(session_id)
        history = session_data.get('messages', [])[-10:]
        regen_config = ablation_config.get('regeneration', {})
        
        result = generator.generate(
            user_input=user_input,
            rag_context=rag_context,
            current_round=round_num,
            api_config=api_config,
            system_prompt=session_config['system_prompt'],
            user_name=session_config['user_name'],
            user_persona=session_config['user_persona'],
            character_name=session_config['character_name'],
            disambiguation_enabled=False,
            regeneration_config=regen_config,
            history=history,
            tuning_config=tuning_config,
            protocol_config=protocol_config
        )
        
        # 5. 将新的向量索引保存到对应 session。
        physical_time = datetime.now().isoformat()
        combined_text = f"{session_config['user_name']}: {user_input}\n{session_config['character_name']}: {result['reply']}"
        log_admin("B", {
            "event": "dialog_regenerate",
            "session_id": session_id,
            "round": round_num,
            "physical_time": physical_time,
            "model": _model_label(api_config),
            "user_name": session_config['user_name'],
            "character_name": session_config['character_name'],
            "user_input": user_input,
            "user_input_with_model": _with_model_prefix(user_input, api_config),
            "assistant_reply": result.get('reply', ''),
            "assistant_reply_with_model": _with_model_prefix(result.get('reply', ''), api_config),
        })
        log_admin("C", {
            "event": "cot_regenerate",
            "session_id": session_id,
            "round": round_num,
            "physical_time": physical_time,
            "model": _model_label(api_config),
            "analysis": result.get('analysis', ''),
            "regeneration_info": result.get('regeneration_info'),
            "protocol_info": result.get('protocol_info'),
        })
        
        chat_atom = {
            "text": combined_text,
            "user_name": session_config['user_name'],
            "character_name": session_config['character_name'],
            "user_input": user_input,
            "assistant_reply": result['reply'],
            "session_id": session_id,
            "timestamp": {"round_num": round_num, "physical_time": physical_time}
        }
        vector_store.add_chat_atom(chat_atom, session_id=session_id)
        
        # 6. 鏇存柊浼氳瘽鏁版嵁
        messages = session_data.get('messages', [])
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].get('round') == round_num and messages[i].get('role') == 'assistant':
                messages[i]['content'] = result['reply']
                messages[i]['timestamp'] = physical_time
                break
        
        memories = session_data.get('memories', [])
        for mem in memories:
            if mem.get('round') == round_num:
                mem['assistant'] = result['reply']
                mem['analysis'] = result.get('analysis', '')
                mem['timestamp'] = physical_time
                break
        
        memory_store.save_session(session_id, session_data)
        
        return jsonify({
            'success': True,
            'reply': result['reply'],
            'analysis': result.get('analysis', ''),
            'config': session_config,  # 返回配置，确保同步。
            'deleted_chunks': len(deleted_chunks),
            'regeneration_info': result.get('regeneration_info'),
            'protocol_info': result.get('protocol_info')
        })
        
    except Exception as e:
        print(f"[ERROR] Regenerate failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'重新生成失败: {str(e)}'}), 500


@chat_bp.route('/api/chat/delete-message', methods=['POST'])
def delete_message():
    """Delete one round of chat messages and its vector index entries."""
    data = request.get_json() or {}
    
    session_id = data.get('session_id')
    round_num = data.get('round')
    
    if not session_id or round_num is None:
        return jsonify({'error': '缺少 session_id 或 round 参数'}), 400
    
    try:
        # 1. 删除向量索引。
        deleted_chunks = vector_store.delete_chat_chunks_by_session_and_round(
            session_id, round_num
        )
        print(f"[Delete] Deleted {len(deleted_chunks)} chunks for session {session_id} round {round_num}")
        
        # 2. 从会话数据中删除消息。
        session_data = memory_store.load_session(session_id)
        messages = session_data.get('messages', [])
        memories = session_data.get('memories', [])
        
        session_data['messages'] = [
            m for m in messages 
            if m.get('round') != round_num
        ]
        session_data['memories'] = [
            m for m in memories 
            if m.get('round') != round_num
        ]
        session_data['last_round'] = max(
            (m.get('round', 0) for m in session_data['messages']),
            default=0
        )
        
        memory_store.save_session(session_id, session_data)
        
        return jsonify({
            'success': True,
            'deleted_chunks': len(deleted_chunks),
            'message': f'已删除轮次 {round_num} 的消息和索引'
        })
        
    except Exception as e:
        print(f"[ERROR] Delete message failed: {e}")
        return jsonify({'error': f'删除失败: {str(e)}'}), 500


@chat_bp.route('/api/test', methods=['POST'])
def test_connection():
    """Test the upstream API connection."""
    data = request.get_json() or {}
    api_key = data.get('api_key', '').strip()
    base_url = data.get('base_url', '').strip()
    model = data.get('model', 'deepseek-chat').strip()
    
    if not api_key:
        return jsonify({'success': False, 'message': 'API Key 不能为空'}), 400
    
    try:
        import openai
        client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url.rstrip('/') if base_url else None,
            timeout=15.0
        )
        client.chat.completions.create(
            model=model,
            messages=[{'role': 'user', 'content': 'hi'}],
            max_tokens=2,
            temperature=0
        )
        return jsonify({'success': True, 'message': '连接成功'})
    except Exception as e:
        error_msg = str(e)
        if '401' in error_msg:
            error_msg = 'API Key 无效'
        elif '404' in error_msg:
            error_msg = '接口地址错误'
        elif 'timeout' in error_msg.lower():
            error_msg = '连接超时'
        return jsonify({'success': False, 'message': error_msg}), 400
