from typing import Dict, Any, Optional
from ...core.base_reward import BaseRewardFunction
from ...core.types import RewardResult

class HeatExchangerReward(BaseRewardFunction):
    def calculate_reward(self, task_params: Dict[str, Any], metrics: Dict[str, float], is_valid: bool = True, error_message: Optional[str] = None) -> RewardResult:
        if not is_valid:
            return RewardResult(normalized_total=0.0, is_valid=False, error_message=error_message)
            
        # Task konfigürasyonundan ağırlıkları çekiyoruz, yoksa eşit (0.5 - 0.5)
        w_heat = task_params.get("w_heat", 0.5)
        w_drop = task_params.get("w_drop", 0.5)
        
        # Hedefleri al
        target_heat = task_params.get("target_heat_duty", 150000.0) # W
        target_drop = task_params.get("max_pressure_drop", 50000.0) # Pa
        
        heat_duty = metrics.get("heat_duty", 0.0)
        pressure_drop = metrics.get("total_pressure_drop", target_drop * 2)
        
        # Heat duty reward: Ne kadar yüksekse o kadar iyi (maksimum 1.0)
        r_heat = min(heat_duty / target_heat, 1.0)
        
        # Pressure drop penalty: Hedefin altındaysa 1.0
        if pressure_drop <= target_drop:
            r_drop = 1.0
        else:
            # Hedefi aştıkça hızla 0'a düşer
            r_drop = max(1.0 - ((pressure_drop - target_drop) / target_drop), 0.0)
            
        total_score = (w_heat * r_heat) + (w_drop * r_drop)
        # normalize to 0.0 - 1.0
        total_weight = w_heat + w_drop
        normalized = total_score / total_weight if total_weight > 0 else 0.0
        
        components = {
            "heat_duty_reward": r_heat,
            "pressure_drop_reward": r_drop
        }
        
        return RewardResult(
            normalized_total=normalized,
            components=components,
            is_valid=True
        )
