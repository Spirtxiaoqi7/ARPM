"""
异步记忆管理
"""

import os
import json
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional


class MemoryAsyncManager:
    def __init__(self, db_path: str = "data/memory_db"):
        self.db_path = db_path
        os.makedirs(self.db_path, exist_ok=True)

    def get_session_file(self, session_id: str) -> str:
        return os.path.join(self.db_path, f"session_{session_id}.json")

    async def save_memory_async(self, session_id: str, round_num: int, content: str, metadata: Optional[Dict] = None):
        await asyncio.sleep(0.1)
        
        session_data = self._load_session(session_id)
        
        memory_entry = {
            "round": round_num,
            "content": content,
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        if "memories" not in session_data:
            session_data["memories"] = []
        
        session_data["memories"].append(memory_entry)
        session_data["last_round"] = round_num
        
        self._save_session(session_id, session_data)

    def get_memory(self, session_id: str, round_num: Optional[int] = None) -> List[Dict]:
        session_data = self._load_session(session_id)
        memories = session_data.get("memories", [])
        
        if round_num is not None:
            return [m for m in memories if m["round"] == round_num]
        return memories

    def get_last_round(self, session_id: str) -> int:
        session_data = self._load_session(session_id)
        return session_data.get("last_round", 0)

    def _load_session(self, session_id: str) -> Dict:
        file_path = self.get_session_file(session_id)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"session_id": session_id, "memories": [], "last_round": 0}

    def _save_session(self, session_id: str, data: Dict):
        file_path = self.get_session_file(session_id)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存会话失败: {e}")


memory_manager = MemoryAsyncManager()
