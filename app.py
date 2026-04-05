"""
ARPM 智能对话系统
"""

import os
import asyncio
import uuid
import json
import threading
import datetime
from flask import Flask, request, jsonify, render_template
from core.memory_async import memory_manager
from modules.llm_client import llm_client
from modules.retriever import retriever
from modules.chunker import chunker
import openai
import logging

# 禁用Flask开发服务器警告
from flask.cli import show_server_banner
show_server_banner = lambda *args, **kwargs: None

# 配置日志 - 隐藏静态文件304状态码
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)  # 只显示错误，隐藏INFO级别的304日志

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
    
    # 消融测试配置
    ablation_config = {
        'arpm_enabled': params.get('arpm_enabled', True),
        'bm25_enabled': params.get('bm25_enabled', True),
        'cot_rerank': params.get('cot_rerank', True),
        'temporal_decay': params.get('temporal_decay', True),
        'keyword_boost': params.get('keyword_boost', True)
    }
    
    # ARPM总开关关闭时，直接返回空检索结果
    if not ablation_config['arpm_enabled']:
        rag_context = []
        app.logger.info("[消融测试] ARPM系统已关闭，使用纯LLM对话")
    else:
        try:
            rag_context = retriever.retrieve(
                user_input, 
                current_round=current_round, 
                k=top_k,
                ablation_config=ablation_config
            )
        except Exception as e:
            app.logger.error(f"检索失败: {e}")
            rag_context = []
    
    # 检查是否有知识库
    has_knowledge = len(retriever.text_chunks) > 0
    
    # 判定逻辑：
    # 1. 第一轮 + 无知识库 -> 静默处理（需要第二轮）
    # 2. 第一轮 + 有知识库 -> 直接输出
    # 3. 第二轮及以后 -> 正常输出（带历史记忆）
    should_silent = (current_round == 1) and (not has_knowledge)
    
    try:
        if should_silent:
            # 无知识库的第一轮：静默分析阶段（ARPM 分析式协议）
            # 消融测试：CoT重排序开关
            cot_rerank = ablation_config.get('cot_rerank', True)
            raw_reply = llm_client.generate(
                user_input,
                rag_context=rag_context,
                is_silent=True,
                api_config=api_config,
                system_prompt=system_prompt,
                cot_rerank=cot_rerank
            )
            
            parsed = llm_client.parse_analysis_response(raw_reply)
            analysis_text = parsed.get('analysis', '')
            response_text = parsed.get('response', raw_reply)
            
            # 保存完整的 analysis + response 到记忆
            memory_content = f"用户: {user_input}\n<analysis>{analysis_text}</analysis>\n<response>{response_text}</response>"
            
            def save_memory():
                try:
                    asyncio.run(memory_manager.save_memory_async(
                        session_id, current_round, memory_content
                    ))
                except Exception as e:
                    app.logger.error(f"存储记忆失败: {e}")
            
            threading.Thread(target=save_memory, daemon=True).start()
            
            # 前端仍保持静默提示，不影响交互习惯
            return jsonify({
                'session_id': session_id,
                'round': current_round,
                'status': 'stored',
                'rag_context': rag_context,
                'reply': '<analysis>首轮分析完成</analysis><response>首轮分析完成，背景知识已存入记忆。请继续第二轮对话获取完整回复。</response>'
            })
        
        else:
            # 有知识库的第一轮，或第二轮及以后
            if current_round == 1:
                # 有知识库的第一轮：直接输出，无历史记忆
                memory_context = None
            else:
                # 第二轮及以后：加载历史记忆
                past_memories = memory_manager.get_memory(session_id)
                memory_context = "\n".join([
                    f"第{m['round']}轮: {m['content'][:500]}"
                    for m in past_memories
                ])
            
            # 消融测试：CoT重排序开关
            cot_rerank = ablation_config.get('cot_rerank', True)
            raw_reply = llm_client.generate(
                user_input,
                rag_context=rag_context,
                memory_context=memory_context,
                current_round=current_round,
                api_config=api_config,
                system_prompt=system_prompt,
                cot_rerank=cot_rerank
            )
            
            parsed = llm_client.parse_analysis_response(raw_reply)
            analysis_text = parsed.get('analysis', '')
            final_reply = parsed.get('response', raw_reply)
            
            # 保存完整的 analysis + response 到记忆，便于后续轮次推理
            memory_content = f"用户: {user_input}\n<analysis>{analysis_text}</analysis>\n<response>{final_reply}</response>"
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
        # 为批量上传的 chunks 补充默认轮次（若缺失）
        for chunk in chunks:
            if "metadata" not in chunk:
                chunk["metadata"] = {}
            if "timestamp" not in chunk["metadata"]:
                chunk["metadata"]["timestamp"] = 1
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
        
        chunks = chunker.split_text(content, metadata={"source": file.filename}, current_round=1)
        
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
        # 返回带元数据的 chunk 列表
        chunks_info = []
        for i, text in enumerate(retriever.text_chunks[:50]):
            meta = retriever.chunk_metadata[i] if i < len(retriever.chunk_metadata) else {}
            chunks_info.append({
                'index': i,
                'text': text[:200] + '...' if len(text) > 200 else text,
                'metadata': meta
            })
        return jsonify({
            'total_chunks': len(retriever.text_chunks),
            'chunks': chunks_info
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


@app.route('/api/knowledge/<int:chunk_idx>/blind', methods=['POST', 'DELETE'])
def set_temporally_blind(chunk_idx):
    """设置/取消时间盲标记"""
    if chunk_idx < 0 or chunk_idx >= len(retriever.text_chunks):
        return jsonify({'error': '无效索引'}), 400
    
    try:
        if request.method == 'POST':
            data = request.get_json() or {}
            blind = data.get('blind', True)
            retriever.set_chunk_temporally_blind(chunk_idx, blind)
            return jsonify({
                'success': True, 
                'chunk_idx': chunk_idx,
                'temporally_blind': blind
            })
        else:  # DELETE
            retriever.set_chunk_temporally_blind(chunk_idx, False)
            return jsonify({
                'success': True,
                'chunk_idx': chunk_idx,
                'temporally_blind': False
            })
    except Exception as e:
        app.logger.error(f"设置时间盲标记失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/knowledge/<int:chunk_idx>/conditions', methods=['GET', 'POST', 'DELETE'])
def manage_conditions(chunk_idx):
    """管理 chunk 的条件激活规则"""
    if chunk_idx < 0 or chunk_idx >= len(retriever.text_chunks):
        return jsonify({'error': '无效索引'}), 400
    
    try:
        if request.method == 'GET':
            # 获取当前条件
            meta = retriever.chunk_metadata[chunk_idx] if chunk_idx < len(retriever.chunk_metadata) else {}
            conditions = meta.get('conditions', {'enabled': False, 'rules': []})
            return jsonify({
                'chunk_idx': chunk_idx,
                'conditions': conditions
            })
        
        elif request.method == 'POST':
            # 设置条件
            data = request.get_json() or {}
            conditions = data.get('conditions', {})
            
            # 验证条件格式
            if 'enabled' not in conditions:
                conditions['enabled'] = True
            if 'logic' not in conditions:
                conditions['logic'] = 'AND'
            if 'rules' not in conditions:
                conditions['rules'] = []
            
            retriever.set_chunk_conditions(chunk_idx, conditions)
            return jsonify({
                'success': True,
                'chunk_idx': chunk_idx,
                'conditions': conditions
            })
        
        else:  # DELETE
            # 清除条件
            retriever.set_chunk_conditions(chunk_idx, {'enabled': False, 'rules': []})
            return jsonify({
                'success': True,
                'chunk_idx': chunk_idx
            })
    except Exception as e:
        app.logger.error(f"管理条件失败: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== 关键词提升 API ====================

@app.route('/api/knowledge/<int:chunk_idx>/keywords', methods=['GET', 'POST', 'DELETE'])
def manage_keywords(chunk_idx):
    """管理 chunk 的关键词列表"""
    if chunk_idx < 0 or chunk_idx >= len(retriever.text_chunks):
        return jsonify({'error': '无效索引'}), 400
    
    try:
        if request.method == 'GET':
            meta = retriever.chunk_metadata[chunk_idx] if chunk_idx < len(retriever.chunk_metadata) else {}
            keywords = meta.get('keywords', [])
            return jsonify({
                'chunk_idx': chunk_idx,
                'keywords': keywords
            })
        
        elif request.method == 'POST':
            data = request.get_json() or {}
            keywords = data.get('keywords', [])
            
            # 验证格式
            valid_keywords = []
            for kw in keywords:
                if isinstance(kw, dict) and 'text' in kw:
                    valid_keywords.append({
                        'text': str(kw['text']),
                        'weight': float(kw.get('weight', 1.5))
                    })
                elif isinstance(kw, str):
                    valid_keywords.append({'text': kw, 'weight': 1.5})
            
            retriever.set_chunk_keywords(chunk_idx, valid_keywords)
            return jsonify({
                'success': True,
                'chunk_idx': chunk_idx,
                'keywords': valid_keywords
            })
        
        else:  # DELETE
            retriever.set_chunk_keywords(chunk_idx, [])
            return jsonify({
                'success': True,
                'chunk_idx': chunk_idx
            })
    except Exception as e:
        app.logger.error(f"管理关键词失败: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== 怀旧模式 API ====================

@app.route('/api/knowledge/<int:chunk_idx>/nostalgia', methods=['GET', 'POST', 'DELETE'])
def manage_nostalgia(chunk_idx):
    """管理 chunk 的怀旧模式设置"""
    if chunk_idx < 0 or chunk_idx >= len(retriever.text_chunks):
        return jsonify({'error': '无效索引'}), 400
    
    try:
        if request.method == 'GET':
            meta = retriever.chunk_metadata[chunk_idx] if chunk_idx < len(retriever.chunk_metadata) else {}
            nostalgia = {
                'enabled': meta.get('nostalgia_enabled', False),
                'factor': meta.get('nostalgia_factor', 0.01)
            }
            return jsonify({
                'chunk_idx': chunk_idx,
                'nostalgia': nostalgia
            })
        
        elif request.method == 'POST':
            data = request.get_json() or {}
            enabled = data.get('enabled', True)
            factor = float(data.get('factor', 0.01))
            
            # 限制因子范围
            factor = max(0.001, min(factor, 0.1))
            
            retriever.set_chunk_nostalgia(chunk_idx, enabled, factor)
            return jsonify({
                'success': True,
                'chunk_idx': chunk_idx,
                'nostalgia': {'enabled': enabled, 'factor': factor}
            })
        
        else:  # DELETE
            retriever.set_chunk_nostalgia(chunk_idx, False, 0.01)
            return jsonify({
                'success': True,
                'chunk_idx': chunk_idx
            })
    except Exception as e:
        app.logger.error(f"管理怀旧模式失败: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== 场景管理 API ====================

@app.route('/api/scenes', methods=['GET', 'POST'])
def manage_scenes():
    """管理场景"""
    try:
        if request.method == 'GET':
            scenes = retriever.get_scenes()
            return jsonify({
                'scenes': scenes
            })
        
        elif request.method == 'POST':
            data = request.get_json() or {}
            start_round = int(data.get('start_round', 1))
            end_round = int(data.get('end_round', start_round))
            title = data.get('title', '')
            summary = data.get('summary', '')
            keywords = data.get('keywords', [])
            
            scene_id = retriever.create_scene(start_round, end_round, title, summary, keywords)
            return jsonify({
                'success': True,
                'scene_id': scene_id
            })
    except Exception as e:
        app.logger.error(f"管理场景失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/scenes/<scene_id>', methods=['DELETE'])
def delete_scene(scene_id):
    """删除场景"""
    try:
        retriever.delete_scene(scene_id)
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"删除场景失败: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== 诊断系统 API ====================

@app.route('/api/diagnostics', methods=['GET', 'POST'])
def run_diagnostics():
    """运行系统诊断"""
    from modules.diagnostics import diagnostics
    
    try:
        if request.method == 'POST':
            data = request.get_json() or {}
            auto_fix = data.get('auto_fix', False)
        else:
            auto_fix = False
        
        report = diagnostics.run_all_checks(auto_fix=auto_fix)
        return jsonify(report)
    except Exception as e:
        app.logger.error(f"诊断失败: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== Chunk 详情 API ====================

@app.route('/api/knowledge/<int:chunk_idx>', methods=['GET'])
def get_chunk_detail(chunk_idx):
    """获取 chunk 详细信息"""
    if chunk_idx < 0 or chunk_idx >= len(retriever.text_chunks):
        return jsonify({'error': '无效索引'}), 400
    
    try:
        info = retriever.get_chunk_info(chunk_idx)
        return jsonify(info)
    except Exception as e:
        app.logger.error(f"获取 chunk 详情失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/knowledge/search', methods=['POST'])
def search_knowledge():
    """使用RAG检索查询知识库"""
    data = request.get_json() or {}
    query = data.get('query', '').strip()
    top_k = min(max(data.get('top_k', 10), 1), 50)
    
    if not query:
        return jsonify({'error': '查询不能为空'}), 400
    
    try:
        # 使用retriever进行RAG检索
        results = retriever.retrieve(query, current_round=1, k=top_k)
        
        # 获取详细的chunk信息
        detailed_results = []
        for result in results:
            chunk_idx = result.get('index', -1)
            if chunk_idx >= 0 and chunk_idx < len(retriever.text_chunks):
                meta = retriever.chunk_metadata[chunk_idx] if chunk_idx < len(retriever.chunk_metadata) else {}
                detailed_results.append({
                    'index': chunk_idx,
                    'text': retriever.text_chunks[chunk_idx],
                    'score': result.get('score', 0),
                    'metadata': {
                        'source': meta.get('source', ''),
                        'timestamp': meta.get('timestamp', 0),
                        'temporally_blind': meta.get('temporally_blind', False),
                        'nostalgia_enabled': meta.get('nostalgia_enabled', False),
                        'keywords': meta.get('keywords', []),
                        'conditions': meta.get('conditions', {}),
                        'scene_id': meta.get('scene_id')
                    }
                })
        
        return jsonify({
            'query': query,
            'total': len(detailed_results),
            'results': detailed_results
        })
    except Exception as e:
        app.logger.error(f"RAG查询失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/knowledge/stats', methods=['GET'])
def get_knowledge_stats():
    """获取知识库统计信息"""
    try:
        chunks = retriever.text_chunks
        metadata = retriever.chunk_metadata
        
        # 统计各类别数量
        stats = {
            'total': len(chunks),
            'blind': 0,
            'nostalgia': 0,
            'conditional': 0,
            'keywords': 0,
            'scene': 0,
            'sources': {}
        }
        
        for meta in metadata:
            if meta.get('temporally_blind'):
                stats['blind'] += 1
            if meta.get('nostalgia_enabled'):
                stats['nostalgia'] += 1
            if meta.get('conditions', {}).get('enabled'):
                stats['conditional'] += 1
            if meta.get('keywords') and len(meta['keywords']) > 0:
                stats['keywords'] += 1
            if meta.get('scene_id'):
                stats['scene'] += 1
            
            # 统计来源
            source = meta.get('source', 'unknown')
            stats['sources'][source] = stats['sources'].get(source, 0) + 1
        
        return jsonify(stats)
    except Exception as e:
        app.logger.error(f"获取统计失败: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== 反馈与归档 API ====================

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """
    接收用户反馈（点赞/差评）
    用于偏好学习，不直接修改AI行为
    """
    data = request.get_json() or {}
    
    feedback_type = data.get('type')  # 'like' or 'dislike'
    message_id = data.get('message_id')
    session_id = data.get('session_id')
    
    if not feedback_type or not message_id:
        return jsonify({'error': '缺少必要参数'}), 400
    
    try:
        # 记录反馈到日志（用于后续分析和偏好学习）
        app.logger.info(f"[用户反馈] 类型: {feedback_type}, 消息ID: {message_id}, 会话: {session_id}")
        
        # 可以扩展：存储到数据库，用于训练偏好模型
        feedback_log = {
            'type': feedback_type,
            'message_id': message_id,
            'session_id': session_id,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        # 保存到反馈日志文件
        feedback_dir = 'data/feedback'
        os.makedirs(feedback_dir, exist_ok=True)
        feedback_file = os.path.join(feedback_dir, f'feedback_{datetime.datetime.now().strftime("%Y%m")}.jsonl')
        
        with open(feedback_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(feedback_log, ensure_ascii=False) + '\n')
        
        return jsonify({'success': True, 'message': '反馈已记录'})
    except Exception as e:
        app.logger.error(f"记录反馈失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/archive', methods=['POST'])
def archive_content():
    """
    归档不合规内容
    保存被举报的内容用于分析
    """
    data = request.get_json() or {}
    
    message_id = data.get('message_id')
    content = data.get('content')
    reason = data.get('reason')
    detail = data.get('detail', '')
    session_id = data.get('session_id')
    
    if not message_id or not content:
        return jsonify({'error': '缺少必要参数'}), 400
    
    try:
        archive_entry = {
            'message_id': message_id,
            'content': content,
            'reason': reason,
            'detail': detail,
            'session_id': session_id,
            'timestamp': datetime.datetime.now().isoformat(),
            'status': 'archived'
        }
        
        # 保存到归档目录
        archive_dir = 'data/archive'
        os.makedirs(archive_dir, exist_ok=True)
        archive_file = os.path.join(archive_dir, f'archived_{datetime.datetime.now().strftime("%Y%m%d")}.jsonl')
        
        with open(archive_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(archive_entry, ensure_ascii=False) + '\n')
        
        app.logger.warning(f"[内容归档] 原因: {reason}, 消息ID: {message_id}")
        
        return jsonify({'success': True, 'message': '内容已归档'})
    except Exception as e:
        app.logger.error(f"归档失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/regenerate', methods=['POST'])
def regenerate_response():
    """
    重新生成回复（用于举报后的内容替换）
    使用安全提示词引导生成合规内容
    """
    data = request.get_json() or {}
    
    user_question = data.get('user_question', '')
    api_config = data.get('api_config', {})
    system_prompt = data.get('system_prompt', '').strip()
    params = data.get('params', {})
    
    if not user_question:
        return jsonify({'error': '缺少用户问题'}), 400
    
    try:
        # 构造安全提示词
        safe_system_prompt = (system_prompt + "\n\n" if system_prompt else "") + \
            "注意：请确保回复内容安全、合规、无害。避免生成任何可能被视为不当、有害或违规的内容。"
        
        # 重新生成（不使用RAG，避免引入可能的问题内容）
        raw_reply = llm_client.generate(
            user_question,
            rag_context=[],  # 不使用RAG上下文，避免引入问题
            memory_context=None,
            current_round=1,
            api_config=api_config,
            system_prompt=safe_system_prompt,
            cot_rerank=False  # 简化生成流程
        )
        
        parsed = llm_client.parse_analysis_response(raw_reply)
        final_reply = parsed.get('response', raw_reply)
        
        app.logger.info(f"[重新生成] 消息已重新生成，长度: {len(final_reply)}")
        
        return jsonify({
            'success': True,
            'reply': final_reply
        })
    except Exception as e:
        app.logger.error(f"重新生成失败: {e}")
        return jsonify({'error': str(e)}), 500


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
    
    # 创建数据目录
    os.makedirs('data/vector_db', exist_ok=True)
    os.makedirs('data/memory_db', exist_ok=True)
    os.makedirs('data/uploads', exist_ok=True)
    os.makedirs('data/feedback', exist_ok=True)
    os.makedirs('data/archive', exist_ok=True)
    
    # 自定义启动信息
    print("=" * 50)
    print(f"  ARPM v3.0 智能对话系统")
    print("=" * 50)
    print(f"  访问地址: http://localhost:{port}")
    print(f"  调试模式: {'开启' if debug else '关闭'}")
    print("=" * 50)
    print("  按 Ctrl+C 停止服务")
    print("")
    
    # 禁用Flask默认启动日志
    import click
    from flask.cli import pass_script_info
    
    def custom_run(**kwargs):
        app.run(**kwargs)
    
    app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False)
