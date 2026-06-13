import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.environments.heat_exchanger.reward import HeatExchangerReward

def test_reward_invalid():
    rew = HeatExchangerReward()
    res = rew.calculate_reward({}, {}, is_valid=False, error_message="DRC Failed")
    assert res.is_valid == False
    assert res.normalized_total == 0.0
    assert "DRC Failed" in res.error_message

def test_reward_valid_perfect():
    rew = HeatExchangerReward()
    task_params = {
        "w_heat": 0.5,
        "w_drop": 0.5,
        "target_heat_duty": 1000.0,
        "max_pressure_drop": 500.0
    }
    metrics = {
        "heat_duty": 2000.0, # Meets and exceeds target
        "total_pressure_drop": 200.0 # Well below max limit
    }
    
    res = rew.calculate_reward(task_params, metrics, is_valid=True)
    assert res.is_valid == True
    # r_heat = min(2000/1000, 1.0) = 1.0
    # r_drop = 1.0 (since 200 <= 500)
    # total = 0.5*1.0 + 0.5*1.0 = 1.0
    assert res.normalized_total == 1.0

def test_reward_valid_penalty():
    rew = HeatExchangerReward()
    task_params = {
        "w_heat": 0.5,
        "w_drop": 0.5,
        "target_heat_duty": 1000.0,
        "max_pressure_drop": 500.0
    }
    metrics = {
        "heat_duty": 500.0, # Half of target
        "total_pressure_drop": 750.0 # Exceeds target
    }
    
    res = rew.calculate_reward(task_params, metrics, is_valid=True)
    assert res.is_valid == True
    # r_heat = min(500/1000, 1.0) = 0.5
    # r_drop = max(1.0 - (750-500)/500, 0.0) = max(1.0 - 0.5, 0) = 0.5
    # total = 0.5*0.5 + 0.5*0.5 = 0.5
    assert res.normalized_total == 0.5
