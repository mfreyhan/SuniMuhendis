from typing import Dict, Any, Optional
from ...core.base_score import BaseScoreFunction
from ...core.types import ScoreResult

class HeatExchangerScoreV1(BaseScoreFunction):
    def calculate_score(self, task_params: Dict[str, Any], metrics: Dict[str, Any], is_valid: bool = True, error_message: Optional[str] = None) -> ScoreResult:
        if not is_valid:
            return ScoreResult(normalized_total=0.0, is_valid=False, error_message=error_message)
            
        # Fetch weights from task configuration, use defaults if not present
        w_heat = task_params.get("w_heat", 0.4)
        w_drop_tube = task_params.get("w_drop_tube", 0.05)
        w_drop_shell = task_params.get("w_drop_shell", 0.05)
        w_eff = task_params.get("w_eff", 0.2)
        w_cost = task_params.get("w_cost", 0.3)
        
        # Get targets
        target_heat = task_params.get("target_heat_duty", 150000.0) # W
        max_dp_tube = task_params.get("max_dp_tube", 50000.0) # Pa
        max_dp_shell = task_params.get("max_dp_shell", 50000.0) # Pa
        
        # Get metrics (Supports both old and new simulator names)
        heat_duty = metrics.get("heat_duty_W", metrics.get("heat_duty", 0.0))
        dp_tube = metrics.get("dp_tube_Pa", metrics.get("pressure_drop_tube", max_dp_tube * 2))
        dp_shell = metrics.get("dp_shell_Pa", metrics.get("pressure_drop_shell", max_dp_shell * 2))
        effectiveness = metrics.get("effectiveness", 0.0)
        cost_annualised = metrics.get("cost_annualised_USD_per_yr", 100000.0)
        num_warnings = metrics.get("num_warnings", 0.0)
        
        # 1. Heat duty score: Higher is better (max 1.0)
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
        
        # 5. Cost score: Lower cost yields higher reward (example baseline 50000 USD/yr)
        # If cost is under 50k it approaches 1.0, decreases if above.
        baseline_cost = 50000.0
        r_cost = min(baseline_cost / max(cost_annualised, 1.0), 1.0)
        
        # Calculate total score
        total_score = (w_heat * r_heat) + (w_drop_tube * r_drop_tube) + (w_drop_shell * r_drop_shell) + (w_eff * r_eff) + (w_cost * r_cost)
        
        # Warnings penalty (10% reduction for each warning)
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

class HeatExchangerScoreV2(BaseScoreFunction):
    def calculate_score(self, task_params: Dict[str, Any], metrics: Dict[str, Any], is_valid: bool = True, error_message: Optional[str] = None) -> ScoreResult:
        if not is_valid:
            return ScoreResult(normalized_total=0.0, is_valid=False, error_message=error_message)
            
        # Fetch weights
        w_heat = task_params.get("w_heat", 0.4)
        w_drop_tube = task_params.get("w_drop_tube", 0.05)
        w_drop_shell = task_params.get("w_drop_shell", 0.05)
        w_eff = task_params.get("w_eff", 0.2)
        w_cost = task_params.get("w_cost", 0.3)
        
        # Fetch targets and parameters
        target_heat = task_params.get("target_heat_duty", 150000.0)
        max_dp_tube = task_params.get("max_dp_tube", 50000.0)
        max_dp_shell = task_params.get("max_dp_shell", 50000.0)
        
        # V2 specific configuration
        target_cost = task_params.get("target_cost", 50000.0)
        oversizing_penalty_factor = task_params.get("oversizing_penalty_factor", 0.5)
        safety_margin = task_params.get("heat_safety_margin", 1.05)
        warning_penalty_per_warning = task_params.get("warning_penalty_per_warning", 0.1)
        dp_decay_factor = task_params.get("dp_decay_factor", 0.2) # Below limit, pressure drop decay
        
        # Get metrics
        heat_duty = metrics.get("heat_duty_W", metrics.get("heat_duty", 0.0))
        dp_tube = metrics.get("dp_tube_Pa", metrics.get("pressure_drop_tube", max_dp_tube * 2))
        dp_shell = metrics.get("dp_shell_Pa", metrics.get("pressure_drop_shell", max_dp_shell * 2))
        effectiveness = metrics.get("effectiveness", 0.0)
        cost_annualised = metrics.get("cost_annualised_USD_per_yr", target_cost * 2)
        num_warnings = metrics.get("num_warnings", 0.0)
        
        # 1. Heat Duty Score
        if heat_duty < target_heat:
            # Under target: quadratic penalty to severely punish missing the spec
            r_heat = (heat_duty / target_heat) ** 2
        else:
            # Over target: safe up to margin, then gradual penalty
            ratio = heat_duty / target_heat
            if ratio <= safety_margin:
                r_heat = 1.0
            else:
                excess_ratio = ratio - safety_margin
                r_heat = max(1.0 - (oversizing_penalty_factor * excess_ratio), 0.0)
                
        # 2. Pressure drop tube score
        if dp_tube <= 0:
            r_drop_tube = 1.0
        elif dp_tube <= max_dp_tube:
            # Linear decay to (1 - dp_decay_factor) at max_dp
            r_drop_tube = 1.0 - (dp_decay_factor * (dp_tube / max_dp_tube))
        else:
            # Rapid decay beyond limit
            r_drop_tube = max(1.0 - dp_decay_factor - ((dp_tube - max_dp_tube) / max_dp_tube), 0.0)
            
        # 3. Pressure drop shell score
        if dp_shell <= 0:
            r_drop_shell = 1.0
        elif dp_shell <= max_dp_shell:
            r_drop_shell = 1.0 - (dp_decay_factor * (dp_shell / max_dp_shell))
        else:
            r_drop_shell = max(1.0 - dp_decay_factor - ((dp_shell - max_dp_shell) / max_dp_shell), 0.0)
            
        # 4. Effectiveness score
        r_eff = min(max(effectiveness, 0.0), 1.0)
        
        # 5. Cost score
        # Target cost gets 1.0. Higher costs get linearly penalized (or inverse).
        if cost_annualised <= target_cost:
            r_cost = 1.0
        else:
            # Drop from 1.0 down to 0.0 if cost is double the target cost.
            r_cost = max(1.0 - ((cost_annualised - target_cost) / target_cost), 0.0)
            
        # Calculate raw total
        total_score = (w_heat * r_heat) + (w_drop_tube * r_drop_tube) + (w_drop_shell * r_drop_shell) + (w_eff * r_eff) + (w_cost * r_cost)
        total_weight = w_heat + w_drop_tube + w_drop_shell + w_eff + w_cost
        
        # Warning penalty 
        penalty_factor = max((1.0 - warning_penalty_per_warning) ** num_warnings, 0.0)
        
        raw_score_before_penalty = total_score / total_weight if total_weight > 0 else 0.0
        normalized = raw_score_before_penalty * penalty_factor
        
        components = {
            "heat_duty_score": r_heat,
            "pressure_drop_tube_score": r_drop_tube,
            "pressure_drop_shell_score": r_drop_shell,
            "effectiveness_score": r_eff,
            "cost_score": r_cost,
            "warning_penalty": penalty_factor,
            "raw_score_before_penalty": raw_score_before_penalty
        }
        
        return ScoreResult(
            normalized_total=normalized,
            components=components,
            is_valid=True
        )

SCORE_REGISTRY = {
    "heat_exchanger_score_v1": HeatExchangerScoreV1,
    "heat_exchanger_score_v2": HeatExchangerScoreV2,
}

def get_score_function(version: str) -> BaseScoreFunction:
    """Returns the instantiated score function based on version string."""
    if version not in SCORE_REGISTRY:
        raise ValueError(f"Unknown score version '{version}'. Available: {list(SCORE_REGISTRY.keys())}")
    return SCORE_REGISTRY[version]()
