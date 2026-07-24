from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from .types import EvaluationResult, ScoreResult
from .base_simulator import BaseSimulator
from .base_score import BaseScoreFunction

class BaseEnvironment(ABC):
    """
    Main environment class combining the simulator, reward function, and DRC validation.
    """
    
    def __init__(self, simulator: BaseSimulator, score_function: BaseScoreFunction):
        self.simulator = simulator
        self.score_function = score_function
        
    @abstractmethod
    def validate_schema(self, design_params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Checks the structural/schema validity of the incoming design.
        E.g., validation via Pydantic model.
        """
        pass
        
    @abstractmethod
    def run_drc(self, design_params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Design Rule Check (DRC). Checks physical/logical constraints.
        """
        pass

    def get_score_function(self, task_params: Dict[str, Any]) -> BaseScoreFunction:
        """
        Returns the score function to be used for the current task.
        By default, returns the environment's default score function.
        Subclasses can override this to support dynamic score functions based on task_params.
        """
        return self.score_function
        
    def evaluate(self, task_id: str, task_params: Dict[str, Any], design_id: str, design_params: Dict[str, Any]) -> EvaluationResult:
        """
        Main evaluation loop.
        """
        score_fn = self.get_score_function(task_params)
        
        # 1. Schema Validation
        schema_valid, schema_err = self.validate_schema(design_params)
        if not schema_valid:
            score = score_fn.calculate_score(task_params, {}, is_valid=False, error_message=schema_err)
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
            score = score_fn.calculate_score(task_params, {}, is_valid=False, error_message=drc_err)
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
                score = score_fn.calculate_score(task_params, {}, is_valid=False, error_message=sim_err)
                return EvaluationResult(
                    task_id=task_id,
                    design_id=design_id,
                    status="simulation_error",
                    score=score,
                    error_message=sim_err
                )
                
            # 4. Score Calculation (Success case)
            score = score_fn.calculate_score(task_params, metrics, is_valid=True)
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
            score = score_fn.calculate_score(task_params, {}, is_valid=False, error_message=error_msg)
            return EvaluationResult(
                task_id=task_id,
                design_id=design_id,
                status="simulation_error",
                score=score,
                error_message=error_msg
            )
