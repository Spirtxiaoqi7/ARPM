"""
ARPM 核心引擎
"""

import math
from typing import Dict, List


class ARPMEngine:
    def __init__(self, decay_rate: float = 20.0, permanent_weight: float = 1.0):
        self.decay_rate = decay_rate
        self.permanent_weight = permanent_weight

    def calculate_time_weight(self, chunk_timestamp: float, current_round: int, is_permanent: bool = False) -> float:
        if is_permanent:
            return self.permanent_weight
        
        delta = abs(current_round - chunk_timestamp)
        return math.exp(-delta / self.decay_rate)

    def apply_arpm_weights(self, retrieval_results: List[Dict], current_round: int) -> List[Dict]:
        weighted_results = []
        
        for result in retrieval_results:
            meta = result.get("metadata", {})
            timestamp = meta.get("timestamp", 0)
            is_permanent = meta.get("permanent", False)
            
            weight = self.calculate_time_weight(timestamp, current_round, is_permanent)
            result["arpm_score"] = result.get("score", 1.0) * weight
            weighted_results.append(result)
        
        weighted_results.sort(key=lambda x: x["arpm_score"], reverse=True)
        return weighted_results


arpm_engine = ARPMEngine()
