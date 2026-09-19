from pydantic import BaseModel, ConfigDict, Field
from typing import Literal, Optional

from .geometry import (
    DEFAULT_PITCH_RATIO,
    DEFAULT_PITCH_TYPE,
    DEFAULT_TUBE_PASSES,
)


class HeatExchangerDesign(BaseModel):
    """
    Heat exchanger design parameters. The LLM is expected to generate JSON in
    this format.

    The seven required fields are the minimum that describes an exchanger, and
    they have never changed: a model that knows only the basics can still
    produce a scoring design.

    The optional fields below are the difference between a working design and a
    good one. They are optional on purpose. Making them required would raise
    the cost of producing *any* valid design, which is the opposite of what the
    benchmark wants to measure — the aim is to reward engineering, not JSON
    compliance. Every default reproduces the simulator's previous behaviour
    exactly, so designs written against the seven-field contract score
    identically to before.
    """
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    # ── Required: the minimum description of an exchanger ────────────
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

    # ── Optional: the levers a better design reaches for ─────────────
    tube_passes: Optional[int] = Field(
        default=None, ge=1,
        description=(
            "Number of tube passes. Must be even for shell-and-tube, and must "
            "divide the tube count. Default {}.".format(DEFAULT_TUBE_PASSES)
        ),
    )
    pitch_ratio: Optional[float] = Field(
        default=None, ge=1.25,
        description=(
            "Tube pitch as a multiple of tube outside diameter. TEMA minimum "
            "1.25. Wider spacing eases shell-side flow but grows the bundle. "
            "Default {}.".format(DEFAULT_PITCH_RATIO)
        ),
    )
    pitch_type: Optional[Literal["triangular", "square", "30deg", "45deg", "60deg", "90deg"]] = Field(
        default=None,
        description="Tube layout pattern. Default '{}'.".format(DEFAULT_PITCH_TYPE),
    )
    baffle_cut: Optional[float] = Field(
        default=None, ge=0.15, le=0.45,
        description=(
            "Baffle cut as a fraction of shell diameter, 0.15 to 0.45. "
            "Default 0.25."
        ),
    )
    D_nozzle_hot: Optional[float] = Field(
        default=None, gt=0.0,
        description=(
            "Hot-side (tube-side) nozzle bore [m]. Too small and nozzle loss "
            "dominates the pressure budget; too large and the stream cannot "
            "distribute. Default 0.05."
        ),
    )
    D_nozzle_cold: Optional[float] = Field(
        default=None, gt=0.0,
        description=(
            "Cold-side (shell-side) nozzle bore [m]. Default 0.05."
        ),
    )
    material: Optional[Literal[
        "carbon_steel", "stainless_304", "stainless_316", "titanium", "cupronickel"
    ]] = Field(
        default=None,
        description="Construction material. Drives cost. Default 'carbon_steel'.",
    )
