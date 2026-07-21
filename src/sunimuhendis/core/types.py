from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class ScoreResult(BaseModel):
    """
    Holds normalized reward values calculated from simulation results.
    """
    normalized_total: float = Field(..., description="Normalized total score.")
    components: Dict[str, float] = Field(default_factory=dict, description="Sub-components of the score function.")
    is_valid: bool = Field(..., description="Whether the design is physically/schema-wise valid.")
    error_message: Optional[str] = Field(None, description="Error message if is_valid is False.")


class EvaluationResult(BaseModel):
    """
    The final evaluation object returned by BaseEnvironment.
    """
    task_id: str = Field(..., description="ID of the evaluated task.")
    design_id: str = Field(default="unknown", description="ID of the evaluated design (if any).")
    status: str = Field(..., description="'success', 'schema_error', 'drc_error', 'simulation_error'")
    error_message: Optional[str] = Field(None, description="Error status message")
    score: ScoreResult
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Raw engineering metrics returned from the simulator.")
    raw_simulation_output: Dict[str, Any] = Field(default_factory=dict, description="Other raw data the simulator might return (optional).")
