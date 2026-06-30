import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.environments.heat_exchanger.score import HeatExchangerScore

def test_reward_invalid():
    rew = HeatExchangerScore()
    res = rew.calculate_score({}, {}, is_valid=False, error_message="DRC Failed")
    assert res.is_valid == False
    assert res.normalized_total == 0.0
    assert "DRC Failed" in res.error_message

def test_reward_valid_perfect():
    rew = HeatExchangerScore()
    task_params = {
        "w_heat": 0.4,
        "w_drop_tube": 0.15,
        "w_drop_shell": 0.15,
        "w_eff": 0.2,
        "w_cost": 0.1,
        "target_heat_duty": 1000.0,
        "max_dp_tube": 500.0,
        "max_dp_shell": 500.0
    }
    metrics = {
        "heat_duty_W": 2000.0, # Meets and exceeds target (1.0)
        "dp_tube_Pa": 200.0, # Below max limit (1.0)
        "dp_shell_Pa": 200.0, # Below max limit (1.0)
        "effectiveness": 1.0, # Max (1.0)
        "cost_annualised_USD_per_yr": 10000.0, # Below baseline 50k (1.0)
        "num_warnings": 0.0 # No penalty
    }
    
    res = rew.calculate_score(task_params, metrics, is_valid=True)
    assert res.is_valid == True
    assert res.normalized_total == 1.0

def test_reward_valid_penalty():
    rew = HeatExchangerScore()
    task_params = {
        "w_heat": 0.4,
        "w_drop_tube": 0.15,
        "w_drop_shell": 0.15,
        "w_eff": 0.2,
        "w_cost": 0.1,
        "target_heat_duty": 1000.0,
        "max_dp_tube": 500.0,
        "max_dp_shell": 500.0
    }
    metrics = {
        "heat_duty_W": 500.0, # Half of target (0.5)
        "dp_tube_Pa": 750.0, # Exceeds target (0.5)
        "dp_shell_Pa": 750.0, # Exceeds target (0.5)
        "effectiveness": 0.5, # Half (0.5)
        "cost_annualised_USD_per_yr": 100000.0, # Double baseline (0.5)
        "num_warnings": 0.0 # No penalty
    }
    
    res = rew.calculate_score(task_params, metrics, is_valid=True)
    assert res.is_valid == True
    # r_heat: 0.5 * 0.4 = 0.2
    # r_drop_tube: 0.5 * 0.15 = 0.075
    # r_drop_shell: 0.5 * 0.15 = 0.075
    # r_eff: 0.5 * 0.2 = 0.1
    # r_cost: 0.5 * 0.1 = 0.05
    # total = 0.5
    assert res.normalized_total == 0.5

