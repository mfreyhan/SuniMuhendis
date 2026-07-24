import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sunimuhendis.environments.registry import make_env
from sunimuhendis.environments.heat_exchanger.env import HeatExchangerEnv
from sunimuhendis.environments.heat_exchanger.score import HeatExchangerScoreV1, HeatExchangerScoreV2

def test_make_env_default():
    env = make_env("heat_exchanger")
    assert isinstance(env, HeatExchangerEnv)
    # Default is V1
    assert isinstance(env.score_function, HeatExchangerScoreV1)

def test_make_env_v2():
    env = make_env("heat_exchanger", score_version="heat_exchanger_score_v2")
    assert isinstance(env, HeatExchangerEnv)
    assert isinstance(env.score_function, HeatExchangerScoreV2)
    
def test_dynamic_score_resolution():
    env = make_env("heat_exchanger")
    assert isinstance(env.score_function, HeatExchangerScoreV1)
    
    # Override in task params
    task_params = {"score_version": "heat_exchanger_score_v2"}
    score_fn = env.get_score_function(task_params)
    assert isinstance(score_fn, HeatExchangerScoreV2)
