"""
会话管理 API 路由 - 多会话隔离版本
- 每个会话有独立的角色配置
- 删除会话时同步删除对应的向量索引
"""
import os
import glob
import uuid
from datetime import datetime
from pathlib import Path
from flask import Blueprint, request, jsonify, send_file

from storage.memory_store import memory_store
from storage.vector_store import vector_store
from config import MEMORY_DB_PATH, VECTOR_DB_PATH, DATA_DIR, FlaskConfig, LLMConfig
from utils.app_logger import get_app_logger

session_bp = Blueprint('session', __name__)
app_logger = get_app_logger()

AVATAR_UPLOAD_ROOT = DATA_DIR / "avatar_uploads"
AVATAR_MAX_BYTES = 2 * 1024 * 1024
AVATAR_ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
AVATAR_ROLES = {"user", "assistant"}
AVATAR_THEMES = {"chat", "research"}


def is_avatar_upload_enabled() -> bool:
    return os.environ.get("ENABLE_AVATAR_UPLOAD", "").lower() == "true"


def get_current_owner_context(req):
    """Return the owner context for avatar resources.

    Future login integration can replace this with the authenticated user id.
    """
    return {
        "owner_scope": "local",
        "owner_id": "default"
    }


def _safe_path_part(value: str, field_name: str) -> str:
    value = str(value or "").strip()
    if not value or "/" in value or "\\" in value or value in {".", ".."} or ".." in value:
        raise ValueError(f"Invalid {field_name}")
    return value


def normalize_theme(theme):
    theme = str(theme or "").strip()
    if theme not in AVATAR_THEMES:
        raise ValueError("theme must be chat or research")
    return theme


def build_display_title(session_name, session_label, session_id=None):
    name = str(session_name or session_id or "").strip()
    label = str(session_label or "").strip()
    if not label or label == name:
        return name
    return f"{name}（{label}）"


def get_avatar_storage_dir(owner_context, session_id, theme):
    owner_scope = _safe_path_part(owner_context.get("owner_scope"), "owner_scope")
    owner_id = _safe_path_part(owner_context.get("owner_id"), "owner_id")
    safe_session_id = _safe_path_part(session_id, "session_id")
    safe_theme = normalize_theme(theme)
    return AVATAR_UPLOAD_ROOT / owner_scope / owner_id / "sessions" / safe_session_id / "themes" / safe_theme


def build_avatar_storage_key(owner_context, session_id, theme, filename):
    owner_scope = _safe_path_part(owner_context.get("owner_scope"), "owner_scope")
    owner_id = _safe_path_part(owner_context.get("owner_id"), "owner_id")
    safe_session_id = _safe_path_part(session_id, "session_id")
    safe_theme = normalize_theme(theme)
    safe_filename = _safe_path_part(filename, "filename")
    return f"{owner_scope}/{owner_id}/sessions/{safe_session_id}/themes/{safe_theme}/{safe_filename}"


def get_avatar_public_url(owner_context, session_id, theme, filename):
    return f"/uploads/avatars/{build_avatar_storage_key(owner_context, session_id, theme, filename)}"


def get_session_theme_profile(session_data, theme):
    theme = normalize_theme(theme)
    ui_settings = session_data.setdefault("ui_settings", {})
    theme_profiles = ui_settings.setdefault("theme_profiles", {})
    profile = theme_profiles.setdefault(theme, {})
    profile.setdefault("avatars", {})
    return profile


def update_session_theme_avatar(session_data, theme, role, avatar_meta):
    profile = get_session_theme_profile(session_data, theme)
    profile.setdefault("avatars", {})[role] = avatar_meta


def clear_session_theme_avatar(session_data, theme, role):
    profile = get_session_theme_profile(session_data, theme)
    profile.setdefault("avatars", {}).pop(role, None)


def assert_avatar_session_access(owner_context, session_id):
    _safe_path_part(session_id, "session_id")
    session_path = Path(MEMORY_DB_PATH) / f"session_{session_id}.json"
    if not session_path.exists():
        raise FileNotFoundError("Session not found")
    return memory_store.load_session(session_id)


def verify_avatar_modify_permission(req, owner_context, session_id):
    if not is_avatar_upload_enabled():
        raise PermissionError("Avatar upload is disabled. Set ENABLE_AVATAR_UPLOAD=true to enable it.")
    return True


def _validate_avatar_role(role):
    if role not in AVATAR_ROLES:
        raise ValueError("role must be user or assistant")
    return role


def _validate_avatar_file(file_storage):
    if not file_storage or not file_storage.filename:
        raise ValueError("Missing avatar file")

    original_name = file_storage.filename or ""
    ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
    if ext not in AVATAR_ALLOWED_EXTENSIONS:
        raise ValueError("Only png, jpg, jpeg and webp images are allowed")

    stream = file_storage.stream
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(0)
    if size <= 0:
        raise ValueError("Avatar file is empty")
    if size > AVATAR_MAX_BYTES:
        raise ValueError("Avatar file must be 2MB or smaller")

    header = stream.read(16)
    stream.seek(0)
    is_png = header.startswith(b"\x89PNG\r\n\x1a\n")
    is_jpeg = header.startswith(b"\xff\xd8\xff")
    is_webp = len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP"
    if not (is_png or is_jpeg or is_webp):
        raise ValueError("Uploaded file is not a supported image")

    if ext == "png" and not is_png:
        raise ValueError("File extension does not match image content")
    if ext in {"jpg", "jpeg"} and not is_jpeg:
        raise ValueError("File extension does not match image content")
    if ext == "webp" and not is_webp:
        raise ValueError("File extension does not match image content")

    return ext


def _safe_avatar_file_path(storage_key):
    parts = [part for part in str(storage_key or "").split("/") if part]
    if not (
        (len(parts) == 7 and parts[2] == "sessions" and parts[4] == "themes" and parts[5] in AVATAR_THEMES)
        or (len(parts) == 5 and parts[2] == "sessions")
    ):
        raise ValueError("Invalid avatar storage key")
    for part in parts:
        _safe_path_part(part, "storage_key")
    ext = parts[-1].rsplit(".", 1)[-1].lower() if "." in parts[-1] else ""
    if ext not in AVATAR_ALLOWED_EXTENSIONS:
        raise ValueError("Invalid avatar file type")

    root = AVATAR_UPLOAD_ROOT.resolve()
    target = (root / Path(*parts)).resolve()
    if os.path.commonpath([str(root), str(target)]) != str(root):
        raise ValueError("Invalid avatar path")
    return target


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


@session_bp.route('/uploads/avatars/<path:storage_key>', methods=['GET'])
def serve_avatar(storage_key):
    """Serve avatar images from the isolated avatar upload root only."""
    try:
        target = _safe_avatar_file_path(storage_key)
        if not target.exists() or not target.is_file():
            return jsonify({'error': 'Avatar not found'}), 404
        return send_file(target)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@session_bp.route('/api/session/<session_id>/avatar', methods=['POST'])
def upload_session_avatar(session_id):
    owner_context = get_current_owner_context(request)
    role = request.form.get('role', '').strip()
    theme = request.form.get('theme', '').strip()
    try:
        session_data = assert_avatar_session_access(owner_context, session_id)
        verify_avatar_modify_permission(request, owner_context, session_id)
        role = _validate_avatar_role(role)
        theme = normalize_theme(theme)
        avatar_file = request.files.get('avatar')
        ext = _validate_avatar_file(avatar_file)

        storage_dir = get_avatar_storage_dir(owner_context, session_id, theme)
        storage_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{role}_avatar_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
        avatar_file.save(storage_dir / filename)

        avatar_info = {
            "url": get_avatar_public_url(owner_context, session_id, theme, filename),
            "storage_key": build_avatar_storage_key(owner_context, session_id, theme, filename),
            "filename": filename,
            "role": role,
            "theme": theme,
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
        update_session_theme_avatar(session_data, theme, role, avatar_info)
        memory_store.save_session(session_id, session_data)
        app_logger.info("avatar upload succeeded session_id=%s theme=%s role=%s", session_id, theme, role)

        return jsonify({
            "success": True,
            "session_id": session_id,
            "role": role,
            "theme": theme,
            "avatar_url": avatar_info["url"],
            "avatar": avatar_info
        })
    except PermissionError as e:
        app_logger.warning("avatar upload rejected session_id=%s theme=%s role=%s reason=%s", session_id, theme, role, str(e))
        return jsonify({"success": False, "error": str(e)}), 403
    except FileNotFoundError as e:
        app_logger.warning("avatar upload failed session_id=%s theme=%s role=%s reason=session_not_found", session_id, theme, role)
        return jsonify({"success": False, "error": str(e)}), 404
    except ValueError as e:
        app_logger.warning("avatar upload rejected session_id=%s theme=%s role=%s reason=%s", session_id, theme, role, str(e))
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        app_logger.exception("avatar upload failed session_id=%s theme=%s role=%s", session_id, theme, role)
        return jsonify({"success": False, "error": str(e)}), 500


@session_bp.route('/api/session/<session_id>/avatar', methods=['DELETE'])
def delete_session_avatar(session_id):
    owner_context = get_current_owner_context(request)
    role = request.args.get('role', '').strip()
    theme = request.args.get('theme', '').strip()
    try:
        session_data = assert_avatar_session_access(owner_context, session_id)
        verify_avatar_modify_permission(request, owner_context, session_id)
        role = _validate_avatar_role(role)
        theme = normalize_theme(theme)

        clear_session_theme_avatar(session_data, theme, role)
        memory_store.save_session(session_id, session_data)
        app_logger.info("avatar deleted session_id=%s theme=%s role=%s", session_id, theme, role)

        return jsonify({
            "success": True,
            "session_id": session_id,
            "role": role,
            "theme": theme
        })
    except PermissionError as e:
        app_logger.warning("avatar delete rejected session_id=%s theme=%s role=%s reason=%s", session_id, theme, role, str(e))
        return jsonify({"success": False, "error": str(e)}), 403
    except FileNotFoundError as e:
        app_logger.warning("avatar delete failed session_id=%s theme=%s role=%s reason=session_not_found", session_id, theme, role)
        return jsonify({"success": False, "error": str(e)}), 404
    except ValueError as e:
        app_logger.warning("avatar delete rejected session_id=%s theme=%s role=%s reason=%s", session_id, theme, role, str(e))
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        app_logger.exception("avatar delete failed session_id=%s theme=%s role=%s", session_id, theme, role)
        return jsonify({"success": False, "error": str(e)}), 500


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
                session_name = session_data.get('session_name') or session_id
                session_label = session_data.get('session_label') or ''
                session['session_id'] = session_id
                session['session_name'] = session_name
                session['session_label'] = session_label
                session['display_title'] = build_display_title(session_name, session_label, session_id)
                session['name'] = session['display_title']
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


@session_bp.route('/api/session/<session_id>/name', methods=['PATCH'])
def rename_session(session_id):
    """Update only the display name for a session."""
    data = request.get_json() or {}
    session_name = str(data.get('session_name', '')).strip()

    if not session_id:
        return jsonify({'success': False, 'error': 'Missing session_id'}), 400
    if not session_name:
        return jsonify({'success': False, 'error': 'Session name cannot be empty'}), 400
    if len(session_name) > 40:
        return jsonify({'success': False, 'error': 'Session name must be 40 characters or fewer'}), 400

    try:
        session_data = memory_store.load_session(session_id)
        session_data['session_name'] = session_name
        memory_store.save_session(session_id, session_data)
        session_label = session_data.get('session_label') or ''
        return jsonify({
            'success': True,
            'session_id': session_id,
            'session_name': session_name,
            'session_label': session_label,
            'display_title': build_display_title(session_name, session_label, session_id)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@session_bp.route('/api/session/<session_id>/label', methods=['PATCH'])
def update_session_label(session_id):
    """Update only the optional display label for a session."""
    data = request.get_json() or {}
    session_label = str(data.get('session_label', '')).strip()

    if not session_id:
        return jsonify({'success': False, 'error': 'Missing session_id'}), 400
    if len(session_label) > 30:
        app_logger.warning("session label update rejected session_id=%s reason=too_long", session_id)
        return jsonify({'success': False, 'error': 'Session label must be 30 characters or fewer'}), 400

    try:
        session_data = memory_store.load_session(session_id)
        session_name = session_data.get('session_name') or session_id
        session_data['session_label'] = session_label
        memory_store.save_session(session_id, session_data)
        app_logger.info("session label updated session_id=%s has_label=%s", session_id, bool(session_label))
        return jsonify({
            'success': True,
            'session_id': session_id,
            'session_name': session_name,
            'session_label': session_label,
            'display_title': build_display_title(session_name, session_label, session_id)
        })
    except Exception as e:
        app_logger.exception("session label update failed session_id=%s", session_id)
        return jsonify({'success': False, 'error': str(e)}), 500


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
            'session_label': data.get('session_label', ''),
            'display_title': build_display_title(data.get('session_name', session_id), data.get('session_label', ''), session_id),
            'messages': data.get('messages', []),
            'last_round': data.get('last_round', 0),
            'memories': data.get('memories', []),
            'ui_settings': data.get('ui_settings', {}),
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
