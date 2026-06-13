from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from .types import EvaluationResult, RewardResult
from .base_simulator import BaseSimulator
from .base_reward import BaseRewardFunction

class BaseEnvironment(ABC):
    """
    Simülatör, ödül fonksiyonu ve DRC doğrulamasını bir araya getiren
    ana ortam (environment) sınıfı.
    """
    
    def __init__(self, simulator: BaseSimulator, reward_function: BaseRewardFunction):
        self.simulator = simulator
        self.reward_function = reward_function
        
    @abstractmethod
    def validate_schema(self, design_params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Gelen tasarımın veri yapısının/şemasının doğruluğunu kontrol eder.
        Örn: Pydantic modeli ile doğrulama.
        """
        pass
        
    @abstractmethod
    def run_drc(self, design_params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Design Rule Check (DRC). Fiziksel/mantıksal sınırlamaları kontrol eder.
        """
        pass
        
    def evaluate(self, task_id: str, task_params: Dict[str, Any], design_id: str, design_params: Dict[str, Any]) -> EvaluationResult:
        """
        Ana değerlendirme döngüsü.
        """
        
        # 1. Schema Validation
        schema_valid, schema_err = self.validate_schema(design_params)
        if not schema_valid:
            reward = self.reward_function.calculate_reward(task_params, {}, is_valid=False, error_message=schema_err)
            return EvaluationResult(
                task_id=task_id,
                design_id=design_id,
                status="schema_error",
                reward=reward,
                error_message=schema_err
            )
            
        # 2. DRC Validation
        drc_valid, drc_err = self.run_drc(design_params)
        if not drc_valid:
            reward = self.reward_function.calculate_reward(task_params, {}, is_valid=False, error_message=drc_err)
            return EvaluationResult(
                task_id=task_id,
                design_id=design_id,
                status="drc_error",
                reward=reward,
                error_message=drc_err
            )
            
        # 3. Simulation
        try:
            success, metrics, raw_data, sim_err = self.simulator.simulate(design_params)
            
            if not success:
                reward = self.reward_function.calculate_reward(task_params, {}, is_valid=False, error_message=sim_err)
                return EvaluationResult(
                    task_id=task_id,
                    design_id=design_id,
                    status="simulation_error",
                    reward=reward,
                    error_message=sim_err
                )
                
            # 4. Reward Calculation (Success case)
            reward = self.reward_function.calculate_reward(task_params, metrics, is_valid=True)
            return EvaluationResult(
                task_id=task_id,
                design_id=design_id,
                status="success",
                reward=reward,
                metrics=metrics,
                raw_simulation_output=raw_data
            )
            
        except Exception as e:
            # Catch unexpected simulator crashes
            error_msg = f"Unexpected simulation crash: {str(e)}"
            reward = self.reward_function.calculate_reward(task_params, {}, is_valid=False, error_message=error_msg)
            return EvaluationResult(
                task_id=task_id,
                design_id=design_id,
                status="simulation_error",
                reward=reward,
                error_message=error_msg
            )
