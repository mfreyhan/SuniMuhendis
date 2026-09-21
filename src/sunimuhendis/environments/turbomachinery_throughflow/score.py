from typing import Any, Dict, Optional
from ...core.base_score import BaseScoreFunction
from ...core.types import ScoreResult

class ExperimentalThroughflowScore(BaseScoreFunction):
    """No training reward until physical acceptance is implemented."""
    def calculate_score(self, task_params: Dict[str, Any], metrics: Dict[str, Any], is_valid: bool=True, error_message: Optional[str]=None) -> ScoreResult:
        return ScoreResult(normalized_total=0.0, components={"experimental_backend": 0.0}, is_valid=is_valid, error_message=error_message)
