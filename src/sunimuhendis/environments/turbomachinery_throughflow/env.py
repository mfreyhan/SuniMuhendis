from typing import Any, Dict, Optional
from pydantic import ValidationError
from ...core.base_environment import BaseEnvironment
from .contracts import ThroughflowDesignV1, ThroughflowTaskV1

class TurbomachineryThroughflowEnv(BaseEnvironment):
    def validate_schema(self, design_params: Dict[str, Any]):
        try: ThroughflowDesignV1.model_validate(design_params); return True,None
        except ValidationError as exc: return False,"Schema Error: {}".format(exc)
    def run_drc(self, design_params: Dict[str, Any]): return True,None
    def prepare_simulation_inputs(self, design_params: Dict[str, Any], task_params: Dict[str, Any]):
        task=ThroughflowTaskV1.model_validate(task_params); design=ThroughflowDesignV1.model_validate(design_params); task.validate_design_ownership(design)
        return {"design":design.model_dump(mode="json"),"task":task.model_dump(mode="json")}
