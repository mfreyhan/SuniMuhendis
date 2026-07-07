from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from .types import EvaluationResult, ScoreResult
from .base_simulator import BaseSimulator
from .base_score import BaseScoreFunction

class BaseEnvironment(ABC):
    """
    Simülatör, ödül fonksiyonu ve DRC doğrulamasını bir araya getiren
    ana ortam (environment) sınıfı.
    """
    
    def __init__(self, simulator: BaseSimulator, score_function: BaseScoreFunction):
        self.simulator = simulator
        self.score_function = score_function
        
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
            score = self.score_function.calculate_score(task_params, {}, is_valid=False, error_message=schema_err)
            return EvaluationResult(
                task_id=task_id,
                design_id=design_id,
                status="schema_error",
                score=score,
                error_message=schema_err
            )
            
        # 2. DRC Validation
        drc_valid, drc_err = self.run_drc(design_params)
        if not drc_valid:
            score = self.score_function.calculate_score(task_params, {}, is_valid=False, error_message=drc_err)
            return EvaluationResult(
                task_id=task_id,
                design_id=design_id,
                status="drc_error",
                score=score,
                error_message=drc_err
            )
            
        # 3. Simulation
        try:
            success, metrics, raw_data, sim_err = self.simulator.simulate(design_params)
            
            if not success:
                score = self.score_function.calculate_score(task_params, {}, is_valid=False, error_message=sim_err)
                return EvaluationResult(
                    task_id=task_id,
                    design_id=design_id,
                    status="simulation_error",
                    score=score,
                    error_message=sim_err
                )
                
            # 4. Score Calculation (Success case)
            score = self.score_function.calculate_score(task_params, metrics, is_valid=True)
            return EvaluationResult(
                task_id=task_id,
                design_id=design_id,
                status="success",
                score=score,
                metrics=metrics,
                raw_simulation_output=raw_data
            )
            
        except Exception as e:
            # Catch unexpected simulator crashes
            error_msg = f"Unexpected simulation crash: {str(e)}"
            score = self.score_function.calculate_score(task_params, {}, is_valid=False, error_message=error_msg)
            return EvaluationResult(
                task_id=task_id,
                design_id=design_id,
                status="simulation_error",
                score=score,
                error_message=error_msg
            )
