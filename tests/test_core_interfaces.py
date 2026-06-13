import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.base_simulator import BaseSimulator
from src.core.base_reward import BaseRewardFunction
from src.core.base_environment import BaseEnvironment
from src.core.types import EvaluationResult, RewardResult
from typing import Dict, Any, Tuple, Optional

class DummySimulator(BaseSimulator):
    def simulate(self, design_params: Dict[str, Any]) -> Tuple[bool, Dict[str, float], Dict[str, Any], str]:
        if design_params.get("fail_sim", False):
            return False, {}, {}, "Simulation failed"
        if design_params.get("crash_sim", False):
            raise ValueError("Crash!")
        return True, {"metric_1": 10.0}, {}, ""

class DummyReward(BaseRewardFunction):
    def calculate_reward(self, task_params: Dict[str, Any], metrics: Dict[str, float], is_valid: bool = True, error_message: Optional[str] = None) -> RewardResult:
        if not is_valid:
            return RewardResult(normalized_total=-1.0, is_valid=False, error_message=error_message)
        return RewardResult(normalized_total=1.0, components={"metric_1": metrics.get("metric_1", 0.0)}, is_valid=True)

class DummyEnvironment(BaseEnvironment):
    def validate_schema(self, design_params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        if "invalid_schema" in design_params:
            return False, "Schema is invalid"
        return True, None
        
    def run_drc(self, design_params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        if "invalid_drc" in design_params:
            return False, "DRC failed"
        return True, None

@pytest.fixture
def dummy_env():
    return DummyEnvironment(DummySimulator(), DummyReward())

def test_successful_evaluation(dummy_env):
    res = dummy_env.evaluate("t1", {}, "d1", {"valid": True})
    assert res.status == "success"
    assert res.reward.is_valid == True
    assert res.reward.normalized_total == 1.0
    assert res.metrics["metric_1"] == 10.0

def test_schema_error(dummy_env):
    res = dummy_env.evaluate("t1", {}, "d2", {"invalid_schema": True})
    assert res.status == "schema_error"
    assert res.reward.is_valid == False
    assert res.reward.normalized_total == -1.0
    assert "Schema is invalid" in res.error_message

def test_drc_error(dummy_env):
    res = dummy_env.evaluate("t1", {}, "d3", {"invalid_drc": True})
    assert res.status == "drc_error"
    assert res.reward.is_valid == False
    assert res.reward.normalized_total == -1.0
    assert "DRC failed" in res.error_message

def test_simulation_failure(dummy_env):
    res = dummy_env.evaluate("t1", {}, "d4", {"fail_sim": True})
    assert res.status == "simulation_error"
    assert res.reward.is_valid == False
    assert res.reward.normalized_total == -1.0
    assert "Simulation failed" in res.error_message

def test_simulation_crash(dummy_env):
    res = dummy_env.evaluate("t1", {}, "d5", {"crash_sim": True})
    assert res.status == "simulation_error"
    assert res.reward.is_valid == False
    assert res.reward.normalized_total == -1.0
    assert "Unexpected simulation crash" in res.error_message
