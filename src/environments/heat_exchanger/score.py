from typing import Dict, Any, Optional
from ...core.base_score import BaseScoreFunction
from ...core.types import ScoreResult

class HeatExchangerScore(BaseScoreFunction):
    def calculate_score(self, task_params: Dict[str, Any], metrics: Dict[str, Any], is_valid: bool = True, error_message: Optional[str] = None) -> ScoreResult:
        if not is_valid:
            return ScoreResult(normalized_total=0.0, is_valid=False, error_message=error_message)
            
        # Task konfigürasyonundan ağırlıkları çekiyoruz, yoksa varsayılan
        w_heat = task_params.get("w_heat", 0.4)
        w_drop_tube = task_params.get("w_drop_tube", 0.05)
        w_drop_shell = task_params.get("w_drop_shell", 0.05)
        w_eff = task_params.get("w_eff", 0.2)
        w_cost = task_params.get("w_cost", 0.3)
        
        # Hedefleri al
        target_heat = task_params.get("target_heat_duty", 150000.0) # W
        max_dp_tube = task_params.get("max_dp_tube", 50000.0) # Pa
        max_dp_shell = task_params.get("max_dp_shell", 50000.0) # Pa
        
        # Metrikleri al (Eski ve yeni simülatör isimlerini destekler)
        heat_duty = metrics.get("heat_duty_W", metrics.get("heat_duty", 0.0))
        dp_tube = metrics.get("dp_tube_Pa", metrics.get("pressure_drop_tube", max_dp_tube * 2))
        dp_shell = metrics.get("dp_shell_Pa", metrics.get("pressure_drop_shell", max_dp_shell * 2))
        effectiveness = metrics.get("effectiveness", 0.0)
        cost_annualised = metrics.get("cost_annualised_USD_per_yr", 100000.0)
        num_warnings = metrics.get("num_warnings", 0.0)
        
        # 1. Heat duty score: Ne kadar yüksekse o kadar iyi (maksimum 1.0)
        r_heat = min(heat_duty / target_heat, 1.0)
        
        # 2. Pressure drop tube penalty
        if dp_tube <= max_dp_tube:
            r_drop_tube = 1.0
        else:
            r_drop_tube = max(1.0 - ((dp_tube - max_dp_tube) / max_dp_tube), 0.0)
            
        # 3. Pressure drop shell penalty
        if dp_shell <= max_dp_shell:
            r_drop_shell = 1.0
        else:
            r_drop_shell = max(1.0 - ((dp_shell - max_dp_shell) / max_dp_shell), 0.0)
            
        # 4. Effectiveness score
        r_eff = min(max(effectiveness, 0.0), 1.0)
        
        # 5. Cost score: Daha düşük maliyet daha yüksek ödül (örnek baseline 50000 USD/yıl)
        # Eğer maliyet 50k altındaysa 1.0'a yaklaşır, üstündeyse azalır.
        baseline_cost = 50000.0
        r_cost = min(baseline_cost / max(cost_annualised, 1.0), 1.0)
        
        # Toplam skoru hesapla
        total_score = (w_heat * r_heat) + (w_drop_tube * r_drop_tube) + (w_drop_shell * r_drop_shell) + (w_eff * r_eff) + (w_cost * r_cost)
        
        # Warnings penalty (her bir uyarı için %10 kesinti)
        penalty_factor = max(1.0 - (num_warnings * 0.1), 0.0)
        
        # normalize
        total_weight = w_heat + w_drop_tube + w_drop_shell + w_eff + w_cost
        normalized = (total_score / total_weight) * penalty_factor if total_weight > 0 else 0.0
        
        components = {
            "heat_duty_reward": r_heat,
            "pressure_drop_tube_reward": r_drop_tube,
            "pressure_drop_shell_reward": r_drop_shell,
            "effectiveness_reward": r_eff,
            "cost_reward": r_cost,
            "penalty_factor": penalty_factor
        }
        
        return ScoreResult(
            normalized_total=normalized,
            components=components,
            is_valid=True
        )
