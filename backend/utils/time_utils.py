"""
时间处理工具 - 双时态系统
"""
from datetime import datetime, timedelta
from typing import Tuple, Optional
import math

class DualTimestamp:
    """双时态时间戳管理"""
    
    @staticmethod
    def now() -> Tuple[int, str]:
        """
        获取当前双时态时间
        返回: (round_num占位符, physical_time)
        注意：round_num需要外部传入
        """
        return (0, datetime.now().isoformat())
    
    @staticmethod
    def format_physical_time(iso_time: str) -> str:
        """格式化物理时间为人类可读"""
        try:
            dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
            return dt.strftime("%Y年%m月%d日 %H:%M")
        except:
            return iso_time
    
    @staticmethod
    def hours_passed(iso_time: str) -> float:
        """计算从iso_time到现在经过的小时数"""
        try:
            dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
            now = datetime.now()
            delta = now - dt
            return delta.total_seconds() / 3600
        except:
            return 0.0

class TemporalWeightCalculator:
    """时态权重计算器"""
    
    def __init__(self, decay_rate_round: float = 20.0, decay_rate_hours: float = 168.0):
        self.decay_rate_round = decay_rate_round
        self.decay_rate_hours = decay_rate_hours
    
    def compute_weight(
        self,
        chunk_round: int,
        chunk_physical_time: str,
        current_round: int,
        scene_id: Optional[str] = None,
        current_scene_id: Optional[str] = None
    ) -> float:
        """
        计算双时态权重
        
        公式: w = exp(-Δround / λ_round) * exp(-Δhours / λ_hours) * scene_factor
        
        Args:
            chunk_round: 块创建的轮次
            chunk_physical_time: 块创建的物理时间(ISO格式)
            current_round: 当前轮次
            scene_id: 块所属场景ID
            current_scene_id: 当前场景ID
        """
        # 轮次衰减
        delta_round = abs(current_round - chunk_round)
        w_round = math.exp(-delta_round / self.decay_rate_round)
        
        # 物理时间衰减
        hours_passed = DualTimestamp.hours_passed(chunk_physical_time)
        w_clock = math.exp(-hours_passed / self.decay_rate_hours)
        
        # 基础权重
        weight = w_round * w_clock
        
        # 跨场景衰减
        if scene_id and current_scene_id and scene_id != current_scene_id:
            weight *= 0.5
        
        return weight


