from typing import Dict, Any, Optional
from pydantic import ValidationError
from ...core.base_environment import BaseEnvironment
from ...core.base_score import BaseScoreFunction
from .schema import HeatExchangerDesign
from .drc import run_heat_exchanger_drc

class HeatExchangerEnv(BaseEnvironment):
    def validate_schema(self, design_params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        try:
            # Validate through Pydantic model
            model = HeatExchangerDesign(**design_params)
            return True, None
        except ValidationError as e:
            return False, f"Schema Error: {str(e)}"
            
    def run_drc(self, design_params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        return run_heat_exchanger_drc(design_params)

    def get_score_function(self, task_params: Dict[str, Any]) -> BaseScoreFunction:
        """
        Overrides base behavior to dynamically select the score version if
        'score_version' is explicitly defined in the task configuration.
        """
        score_version = task_params.get("score_version")
        if score_version:
            from .score import get_score_function
            return get_score_function(score_version)
        return self.score_function
