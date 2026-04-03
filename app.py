"""
ARPM 智能对话系统
"""

import os
import asyncio
import uuid
import json
import threading
from flask import Flask, request, jsonify, render_template
from core.memory_async import memory_manager
from modules.llm_client import llm_client
from modules.retriever import retriever
from modules.chunker import chunker
import openai

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.urandom(24)

# 默认配置
DEFAULT_CONFIG = {
    'PORT': 5000,
    'DEBUG': True,
    'CHUNK_SIZE': 600,
    'CHUNK_OVERLAP': 100,
    'DECAY_RATE': 20.0,
    'PERMANENT_WEIGHT': 1.0,
    'RETRIEVAL_K': 5
}

for key, value in DEFAULT_CONFIG.items():
    os.environ.setdefault(key, str(value))


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/test', methods=['POST'])
def test_connection():
    data = request.get_json() or {}
    api_key = data.get('api_key', '').strip()
    base_url = data.get('base_url', '').strip()
    model = data.get('model', 'deepseek-chat').strip()

    if not api_key:
        return jsonify({'success': False, 'message': 'API Key 不能为空'}), 400

    try:
        final_base_url = base_url if base_url else None
        if final_base_url:
            final_base_url = final_base_url.rstrip('/')
        
        client = openai.OpenAI(api_key=api_key, base_url=final_base_url, timeout=15.0)
        client.chat.completions.create(
            model=model,
            messages=[{'role': 'user', 'content': 'hi'}],
            max_tokens=2,
            temperature=0
        )
        return jsonify({'success': True, 'message': '连接成功'})
        
    except Exception as e:
        error_msg = str(e)
        if "Connection error" in error_msg or "connect" in error_msg.lower():
            error_msg = "网络连接失败"
        elif "401" in error_msg:
            error_msg = "API Key 无效"
        elif "404" in error_msg:
            error_msg = "接口地址错误"
        elif "timeout" in error_msg.lower():
            error_msg = "连接超时"
            
        return jsonify({'success': False, 'message': error_msg}), 400


@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json() or {}
    
    user_input = data.get('message', '').strip()
    if not user_input:
        return jsonify({'error': '消息不能为空'}), 400
    
    if len(user_input) > 10000:
        return jsonify({'error': '消息过长'}), 400
    
    session_id = data.get('session_id') or str(uuid.uuid4())
    current_round = data.get('round', 1)
    api_config = data.get('api_config', {})
    params = data.get('params', {})
    system_prompt = data.get('system_prompt', '').strip()
    
    if not isinstance(current_round, int) or current_round < 1:
        current_round = 1
    
    top_k = min(max(params.get('top_k', 5), 1), 20)
    
    try:
        rag_context = retriever.retrieve(user_input, current_round=current_round, k=top_k)
    except Exception as e:
        app.logger.error(f"检索失败: {e}")
        rag_context = []
    
    if current_round == 1:
        try:
            llm_reply = llm_client.generate(
                user_input,
                rag_context=rag_context,
                is_silent=True,
                api_config=api_config,
                system_prompt=system_prompt
            )
            
            memory_content = f"用户: {user_input}\n助手: {llm_reply}"
            
            def save_memory():
                try:
                    asyncio.run(memory_manager.save_memory_async(
                        session_id, current_round, memory_content
                    ))
                except Exception as e:
                    app.logger.error(f"存储记忆失败: {e}")
            
            threading.Thread(target=save_memory, daemon=True).start()
            
            return jsonify({
                'session_id': session_id,
                'round': current_round,
                'status': 'stored',
                'rag_context': rag_context,
                'reply': '<analysis>首轮分析完成</analysis><response>首轮分析完成，背景知识已存入记忆。请继续第二轮对话获取完整回复。</response>'
            })
            
        except Exception as e:
            app.logger.error(f"处理失败: {e}")
            return jsonify({'error': '处理失败', 'message': str(e)}), 500
    else:
        try:
            past_memories = memory_manager.get_memory(session_id)
            memory_str = "\n".join([
                f"第{m['round']}轮: {m['content'][:500]}"
                for m in past_memories
            ])
            
            final_reply = llm_client.generate(
                user_input,
                rag_context=rag_context,
                memory_context=memory_str,
                current_round=current_round,
                api_config=api_config,
                system_prompt=system_prompt
            )
            
            return jsonify({
                'session_id': session_id,
                'round': current_round,
                'status': 'success',
                'rag_context': rag_context,
                'reply': final_reply
            })
            
        except Exception as e:
            app.logger.error(f"生成失败: {e}")
            return jsonify({'error': '生成失败', 'message': str(e)}), 500


@app.route('/api/upload_batch', methods=['POST'])
def upload_batch():
    data = request.get_json() or {}
    chunks = data.get('chunks', [])
    
    if not chunks:
        return jsonify({'error': '无数据'}), 400
    
    if len(chunks) > 1000:
        return jsonify({'error': '单次超过1000个块'}), 400
    
    try:
        retriever.add_chunks(chunks)
        retriever.save_to_disk()
        return jsonify({'success': True, 'count': len(chunks)})
    except Exception as e:
        app.logger.error(f"上传失败: {e}")
        return jsonify({'error': f'上传失败: {str(e)}'}), 500


@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': '无文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > 5 * 1024 * 1024:
        return jsonify({'error': '文件超过5MB'}), 400
    
    try:
        content = file.read().decode('utf-8')
        if not content.strip():
            return jsonify({'error': '文件为空'}), 400
        
        chunks = chunker.split_text(content, metadata={"source": file.filename})
        
        if not chunks:
            return jsonify({'error': '无有效内容'}), 400
        
        retriever.add_chunks(chunks)
        retriever.save_to_disk()
        
        return jsonify({
            'success': True,
            'count': len(chunks),
            'filename': file.filename
        })
        
    except UnicodeDecodeError:
        return jsonify({'error': '编码错误，请使用 UTF-8'}), 400
    except Exception as e:
        app.logger.error(f"上传失败: {e}")
        return jsonify({'error': f'处理失败: {str(e)}'}), 500


@app.route('/api/knowledge', methods=['GET', 'DELETE'])
def manage_knowledge():
    if request.method == 'GET':
        return jsonify({
            'total_chunks': len(retriever.text_chunks),
            'chunks': retriever.text_chunks[:50]
        })
    
    elif request.method == 'DELETE':
        idx = request.args.get('index', type=int)
        if idx is None or idx < 0 or idx >= len(retriever.text_chunks):
            return jsonify({'error': '无效索引'}), 400
        
        try:
            retriever.delete_chunk(idx)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': f'删除失败: {str(e)}'}), 500


@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """获取会话列表，返回更友好的名称"""
    sessions = []
    db_path = 'data/memory_db'
    
    try:
        if os.path.exists(db_path):
            files = sorted(os.listdir(db_path), reverse=True)
            for f in files:
                if f.startswith('session_') and f.endswith('.json'):
                    sid = f.replace('session_', '').replace('.json', '')
                    
                    # 尝试读取会话名称
                    session_name = None
                    msg_count = 0
                    try:
                        session_data = memory_manager._load_session(sid)
                        session_name = session_data.get('session_name')
                        messages = session_data.get('messages', [])
                        msg_count = len(messages)
                    except Exception:
                        pass
                    
                    # 如果没有保存的名称，从ID解析
                    if not session_name and len(sid) >= 13:
                        # 格式: YYMMDD-HHMM-XXX
                        try:
                            date_part = sid[:6]
                            time_part = sid[7:11]
                            year = '20' + date_part[:2]
                            month = date_part[2:4]
                            day = date_part[4:6]
                            hour = time_part[:2]
                            minute = time_part[2:4]
                            display_name = f"{month}月{day}日 {hour}:{minute}"
                        except Exception:
                            display_name = f"会话 {sid[:8]}"
                    else:
                        display_name = session_name or f"会话 {sid[:8]}"
                    
                    sessions.append({
                        'id': sid,
                        'name': display_name,
                        'display_name': display_name,
                        'msg_count': msg_count
                    })
    except Exception as e:
        app.logger.error(f"获取会话失败: {e}")
    
    return jsonify(sessions)


@app.route('/api/session/<session_id>', methods=['GET', 'DELETE'])
def manage_session(session_id):
    if request.method == 'GET':
        try:
            memories = memory_manager.get_memory(session_id)
            return jsonify({'session_id': session_id, 'memories': memories})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'DELETE':
        try:
            file_path = memory_manager.get_session_file(session_id)
            if os.path.exists(file_path):
                os.remove(file_path)
                return jsonify({'success': True})
            return jsonify({'error': '会话不存在'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@app.route('/api/history', methods=['POST'])
def save_history():
    """保存完整对话历史"""
    data = request.get_json() or {}
    session_id = data.get('session_id')
    messages = data.get('messages', [])
    
    if not session_id:
        return jsonify({'error': '缺少会话ID'}), 400
    
    try:
        session_data = memory_manager._load_session(session_id)
        session_data['messages'] = messages
        
        # 如果没有会话名称，生成一个
        if 'session_name' not in session_data or not session_data['session_name']:
            session_data['session_name'] = _generate_session_name()
        
        memory_manager._save_session(session_id, session_data)
        return jsonify({'success': True, 'session_name': session_data['session_name']})
    except Exception as e:
        app.logger.error(f"保存历史失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/history/<session_id>', methods=['GET'])
def get_history(session_id):
    """获取完整对话历史"""
    try:
        session_data = memory_manager._load_session(session_id)
        return jsonify({
            'session_id': session_id,
            'session_name': session_data.get('session_name', session_id),
            'messages': session_data.get('messages', []),
            'last_round': session_data.get('last_round', 0),
            'memories': session_data.get('memories', [])
        })
    except Exception as e:
        app.logger.error(f"获取历史失败: {e}")
        return jsonify({'error': str(e)}), 500


def _generate_session_name():
    """生成友好的会话名称: MM月DD日 HH:MM"""
    from datetime import datetime
    now = datetime.now()
    return now.strftime("%m月%d日 %H:%M")


@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': '接口不存在'}), 404


@app.errorhandler(500)
def internal_error(e):
    app.logger.error(f"服务器错误: {e}")
    return jsonify({'error': '服务器错误'}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    print(f"ARPM 服务启动: http://localhost:{port}")
    
    os.makedirs('data/vector_db', exist_ok=True)
    os.makedirs('data/memory_db', exist_ok=True)
    os.makedirs('data/uploads', exist_ok=True)
    
    app.run(host='0.0.0.0', port=port, debug=debug)
