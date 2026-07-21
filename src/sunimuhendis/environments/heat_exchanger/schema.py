from pydantic import BaseModel, Field
from typing import Literal

class HeatExchangerDesign(BaseModel):
    """
    Represents Heat Exchanger design parameters.
    The LLM is expected to generate JSON in this format.
    """
    geometry_type: Literal["concentric_tube", "shell_and_tube"] = Field(
        ..., description="Must be 'concentric_tube' or 'shell_and_tube'."
    )
    length: float = Field(..., gt=0.0, description="Tube/Shell length [m]")
    inner_tube_di: float = Field(..., gt=0.0, description="Inner tube inner diameter [m]")
    inner_tube_do: float = Field(..., gt=0.0, description="Inner tube outer diameter [m]")
    outer_shell_di: float = Field(..., gt=0.0, description="Outer shell inner diameter [m]")
    number_of_tubes: int = Field(
        default=1, ge=1, description="Number of tubes (1 for concentric, > 1 for shell-and-tube)"
    )
    baffle_spacing: float = Field(
        default=0.0, ge=0.0, description="Baffle spacing [m] (Only applicable for shell-and-tube)"
    )
