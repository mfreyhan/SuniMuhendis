import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sunimuhendis.environments.heat_exchanger.score import HeatExchangerScoreV2

def test_v2_bounds():
    rew = HeatExchangerScoreV2()
    task_params = {
        "w_heat": 0.4,
        "w_drop_tube": 0.15,
        "w_drop_shell": 0.15,
        "w_eff": 0.2,
        "w_cost": 0.1,
        "target_heat_duty": 1000.0,
        "max_dp_tube": 500.0,
        "max_dp_shell": 500.0,
        "target_cost": 50000.0,
        "oversizing_penalty_factor": 0.5,
        "heat_safety_margin": 1.05,
        "warning_penalty_per_warning": 0.1,
        "dp_decay_factor": 0.2
    }
    metrics = {
        "heat_duty_W": 1000.0, # Meets exactly (1.0)
        "dp_tube_Pa": 0.0, # 0 gives 1.0
        "dp_shell_Pa": 0.0, # 0 gives 1.0
        "effectiveness": 1.0, # Max (1.0)
        "cost_annualised_USD_per_yr": 50000.0, # Meets target exactly (1.0)
        "num_warnings": 0.0 # No penalty
    }
    
    res = rew.calculate_score(task_params, metrics, is_valid=True)
    assert res.is_valid == True
    assert res.normalized_total == 1.0

def test_v2_oversizing_penalty():
    rew = HeatExchangerScoreV2()
    task_params = {
        "w_heat": 1.0, "w_drop_tube": 0, "w_drop_shell": 0, "w_eff": 0, "w_cost": 0,
        "target_heat_duty": 1000.0,
        "oversizing_penalty_factor": 0.5,
        "heat_safety_margin": 1.05
    }
    
    # Exactly on target
    res_1 = rew.calculate_score(task_params, {"heat_duty_W": 1000.0})
    assert res_1.normalized_total == 1.0
    
    # Within safety margin (1.05x)
    res_2 = rew.calculate_score(task_params, {"heat_duty_W": 1050.0})
    assert res_2.normalized_total == 1.0
    
    # Beyond safety margin, should penalize
    res_3 = rew.calculate_score(task_params, {"heat_duty_W": 1250.0})
    # ratio = 1.25. excess = 0.20. penalty = 0.5 * 0.20 = 0.10. Score = 0.90
    assert abs(res_3.normalized_total - 0.90) < 1e-6
    
    # Under target, should penalize aggressively
    res_4 = rew.calculate_score(task_params, {"heat_duty_W": 500.0})
    # ratio = 0.5. (0.5)^2 = 0.25
    assert abs(res_4.normalized_total - 0.25) < 1e-6

def test_v2_dp_decay():
    rew = HeatExchangerScoreV2()
    task_params = {
        "w_heat": 0, "w_drop_tube": 1.0, "w_drop_shell": 0, "w_eff": 0, "w_cost": 0,
        "max_dp_tube": 1000.0,
        "dp_decay_factor": 0.2
    }
    
    # 0 pressure drop gives 1.0
    res_1 = rew.calculate_score(task_params, {"dp_tube_Pa": 0.0})
    assert res_1.normalized_total == 1.0
    
    # Half of limit gives 0.9
    res_2 = rew.calculate_score(task_params, {"dp_tube_Pa": 500.0})
    assert abs(res_2.normalized_total - 0.9) < 1e-6
    
    # Exactly at limit gives 0.8
    res_3 = rew.calculate_score(task_params, {"dp_tube_Pa": 1000.0})
    assert abs(res_3.normalized_total - 0.8) < 1e-6
    
    # Over limit drops quickly
    res_4 = rew.calculate_score(task_params, {"dp_tube_Pa": 1500.0})
    # 1.0 - 0.2 - 0.5 = 0.3
    assert abs(res_4.normalized_total - 0.3) < 1e-6
