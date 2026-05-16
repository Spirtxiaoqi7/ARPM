"""
会话记忆存储 - 异步写入优化
"""
import os
import json
import asyncio
from typing import List, Dict, Optional
from datetime import datetime

from config import MEMORY_DB_PATH
from utils.app_logger import get_app_logger

app_logger = get_app_logger()

class MemoryStore:
    """会话记忆存储器"""
    
    def __init__(self):
        os.makedirs(MEMORY_DB_PATH, exist_ok=True)
    
    def _get_session_path(self, session_id: str) -> str:
        return os.path.join(MEMORY_DB_PATH, f"session_{session_id}.json")
    
    def load_session(self, session_id: str) -> Dict:
        """加载会话数据"""
        path = self._get_session_path(session_id)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[ERROR] Failed to load session {session_id}: {e}")
                app_logger.exception("failed to load session session_id=%s", session_id)
        
        # 返回默认结构
        return {
            "session_id": session_id,
            "session_name": None,
            "created_at": datetime.now().isoformat(),
            "last_round": 0,
            "current_scene_id": None,
            "messages": [],
            "memories": []
        }
    
    def save_session(self, session_id: str, data: Dict):
        """同步保存会话（用于关键操作）"""
        path = self._get_session_path(session_id)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ERROR] Failed to save session {session_id}: {e}")
            app_logger.exception("failed to save session session_id=%s", session_id)
    
    async def save_session_async(self, session_id: str, data: Dict):
        """异步保存会话（用于非关键操作）"""
        await asyncio.sleep(0.01)  # 让出控制权
        self.save_session(session_id, data)
    
    def get_all_sessions(self) -> List[Dict]:
        """获取所有会话列表"""
        sessions = []
        try:
            for filename in os.listdir(MEMORY_DB_PATH):
                if filename.startswith("session_") and filename.endswith(".json"):
                    session_id = filename[8:-5]  # 提取ID
                    data = self.load_session(session_id)
                    sessions.append({
                        "id": session_id,
                        "name": data.get("session_name", session_id),
                        "last_round": data.get("last_round", 0),
                        "created_at": data.get("created_at", "")
                    })
        except Exception as e:
            print(f"[ERROR] Failed to list sessions: {e}")
            app_logger.exception("failed to list sessions")
        
        # 按时间倒序
        sessions.sort(key=lambda x: x["created_at"], reverse=True)
        return sessions
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        path = self._get_session_path(session_id)
        if os.path.exists(path):
            try:
                os.remove(path)
                return True
            except Exception as e:
                print(f"[ERROR] Failed to delete session {session_id}: {e}")
                app_logger.exception("failed to delete session session_id=%s", session_id)
        return False
    
    def generate_session_name(self) -> str:
        """生成友好会话名"""
        now = datetime.now()
        return now.strftime("%m月%d日 %H:%M")

# 全局实例
memory_store = MemoryStore()
