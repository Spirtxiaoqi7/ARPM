"""
记忆管理器 - 双时态权重
"""
import math
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from utils.time_utils import DualTimestamp
from config import RetrievalConfig

class MemoryManager:
    """记忆管理器 - 负责权重计算和时态管理"""
    
    def __init__(self):
        self.config = RetrievalConfig()
        self.time_calc = DualTimestamp()
    
    def compute_temporal_weight(
        self,
        chunk_timestamp: Dict,
        current_round: int,
        current_scene_id: Optional[str] = None,
        tuning_config: Optional[Dict] = None
    ) -> float:
        """
        计算双时态权重
        
        公式: w = exp(-Δround / λ_round) * exp(-Δhours / λ_hours)
        
        Args:
            chunk_timestamp: {"round_num": int, "physical_time": str}
            current_round: 当前轮次
            current_scene_id: 当前场景ID (保留参数但暂不启用，见 apply_weights_to_results 注释)
        
        Returns:
            float: 权重值 (0-1]
        """
        # 轮次衰减
        chunk_round = chunk_timestamp.get("round_num", 1)
        delta_round = abs(current_round - chunk_round)
        tuning = tuning_config or {}
        decay_round = float(tuning.get("decay_rate_round", self.config.DECAY_RATE_ROUND))
        decay_hours = float(tuning.get("decay_rate_hours", self.config.DECAY_RATE_HOURS))
        w_round = math.exp(-delta_round / decay_round)
        
        # 物理时间衰减
        physical_time = chunk_timestamp.get("physical_time", "")
        hours_passed = self.time_calc.hours_passed(physical_time)
        w_clock = math.exp(-hours_passed / decay_hours)
        
        # 基础权重（已移除场景因子，见下方注释）
        weight = w_round * w_clock
        
        return weight
    
    def apply_weights_to_results(
        self,
        results: List[Dict],
        current_round: int,
        current_scene_id: Optional[str] = None,
        temporal_enabled: bool = True,
        tuning_config: Optional[Dict] = None
    ) -> List[Dict]:
        """
        对检索结果应用时态权重（支持消融开关）

        说明：
        - 这里只处理检索结果的分数重排，不负责写入
        - 知识库结果和对话历史结果会分别调用本方法，各自独立计算权重
        - 对话原子写入由 chat.py -> vector_store.add_chat_atom() 独立负责
        
        [注意] 场景隔离功能接口已保留但暂不启用
        - current_scene_id 参数保留用于未来扩展
        - scene_factor 固定返回 1.0（即不应用场景衰减）
        - 如需启用场景功能，需完善 scene_id 的数据存储链路
        
        Args:
            results: 检索结果列表，每项包含timestamp和score
            current_round: 当前轮次
            current_scene_id: 当前场景ID (保留接口，暂不启用)
            temporal_enabled: 双时态开关，False时不应用时间衰减（所有权重=1.0）
        
        Returns:
            按加权分数排序的结果
        """
        weighted = []
        for result in results:
            timestamp = result.get("timestamp", {"round_num": 1, "physical_time": ""})
            
            # 双时态开关控制
            if temporal_enabled:
                # 计算时态权重
                temporal_w = self.compute_temporal_weight(
                    timestamp, current_round, current_scene_id, tuning_config=tuning_config
                )
            else:
                # 时态关闭：所有权重为1.0（纯RAG，无时间遗忘）
                temporal_w = 1.0
            
            # [接口保留] 场景因子 - 暂不启用
            # 原因：scene_id 数据存储链路不完整，保存对话时未写入 scene_id
            # 如需启用，需修改：
            #   1. chat.py - 保存对话原子块时传入 scene_id
            #   2. vector_store.py - 存储和返回 scene_id
            scene_factor = 1.0  # 固定为1.0，即不应用场景衰减
            
            # 最终加权分数（仅时态权重）
            original_score = result.get("score", 1.0)
            weighted_score = original_score * temporal_w  # 已移除 scene_factor
            
            result["weighted_score"] = weighted_score
            result["temporal_weight"] = temporal_w
            result["scene_factor"] = scene_factor  # 保留字段，固定为1.0
            result["temporal_enabled"] = temporal_enabled
            weighted.append(result)
        
        # 按加权分数排序
        weighted.sort(key=lambda x: x["weighted_score"], reverse=True)
        return weighted
    
    def build_time_aware_prompt(
        self,
        context_chunks: List[Dict],
        current_time: str
    ) -> str:
        """
        构建带时间信息的Prompt
        让AI能够基于物理时间排序事件
        
        Args:
            context_chunks: 检索到的上下文块
            current_time: 当前物理时间
        
        Returns:
            格式化的时间感知上下文
        """
        lines = [
            f"[当前时间: {current_time}]",
            "",
            "=== 相关背景信息（按时间排序）===",
            ""
        ]
        
        # 按物理时间排序
        sorted_chunks = sorted(
            context_chunks,
            key=lambda x: x.get("timestamp", {}).get("physical_time", ""),
            reverse=True  # 最近的在前
        )
        
        for i, chunk in enumerate(sorted_chunks, 1):
            ts = chunk.get("timestamp", {})
            physical_time = ts.get("physical_time", "")
            round_num = ts.get("round_num", 0)
            
            # 格式化时间
            try:
                dt = datetime.fromisoformat(physical_time.replace('Z', '+00:00'))
                time_str = dt.strftime("%m月%d日 %H:%M")
            except:
                time_str = physical_time
            
            source_type = "对话历史" if chunk.get("source_type") == "chat" else "知识库"
            
            lines.append(f"[{i}] {source_type} | 时间:{time_str} | 轮次:{round_num}")
            lines.append(f"{chunk.get('text', '')[:300]}...")
            lines.append("")
        
        return "\n".join(lines)
    
    def format_physical_time_for_prompt(self) -> str:
        """获取当前物理时间，用于写入Prompt"""
        now = datetime.now()
        return now.strftime("%Y年%m月%d日 %H:%M")

# 全局实例
memory_manager = MemoryManager()
