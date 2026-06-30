import json
import os
import pytest
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.environments.heat_exchanger.env import HeatExchangerEnv
from src.environments.heat_exchanger.simulator import HeatExchangerSimulator
from src.environments.heat_exchanger.score import HeatExchangerScore

def test_smoke_valid_design():
    task_path = os.path.join(os.path.dirname(__file__), '../configs/tasks/heat_exchanger/task_001.json')
    design_path = os.path.join(os.path.dirname(__file__), '../examples/designs/heat_exchanger_valid_001.json')
    
    with open(task_path, 'r') as f:
        task_params = json.load(f)
        
    with open(design_path, 'r') as f:
        design_params = json.load(f)
        
    env = HeatExchangerEnv(
        simulator=HeatExchangerSimulator(),
        score_function=HeatExchangerScore()
    )
    
    # 1st run
    res1 = env.evaluate("task_001", task_params, "valid_design_001", design_params)
    assert res1.status == "success", f"Simulation failed: {res1.error_message}"
    assert res1.score.is_valid == True
    assert "heat_duty_W" in res1.metrics
    assert res1.score.normalized_total >= 0.0
    
    # 2nd run (Determinism check)
    res2 = env.evaluate("task_001", task_params, "valid_design_001", design_params)
    assert res1.metrics["heat_duty_W"] == res2.metrics["heat_duty_W"]
    assert res1.score.normalized_total == res2.score.normalized_total

def test_smoke_concentric_tube_design():
    # Test concentric tube as well
    design_params = {
      "geometry_type": "concentric_tube",
      "length": 5.0,
      "inner_tube_di": 0.02,
      "inner_tube_do": 0.025,
      "outer_shell_di": 0.05,
      "number_of_tubes": 1,
      "baffle_spacing": 0.0
    }
    task_params = {"w_heat": 0.5, "w_drop": 0.5, "target_heat_duty": 150000.0, "max_pressure_drop": 50000.0}
    env = HeatExchangerEnv(HeatExchangerSimulator(), HeatExchangerScore())
    
    res = env.evaluate("task_001", task_params, "concentric_001", design_params)
    assert res.status == "success", f"Concentric simulation failed: {res.error_message}"
    assert "heat_duty_W" in res.metrics
