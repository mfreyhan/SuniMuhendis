"""Versioned SI-unit contracts. The NASA backend is not registered yet."""
from enum import Enum
import math
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
class MachineType(str, Enum): turbine="turbine"; compressor="compressor"
class FlowPath(str, Enum): axial="axial"; radial="radial"; mixed="mixed"
class RowType(str, Enum): inlet="inlet"; stator="stator"; rotor="rotor"; outlet="outlet"
class LossModel(str, Enum):
    fixed_pressure="fixed_pressure"; diffusion="diffusion"; td2="td2"; kacker_okapuu="kacker_okapuu"; ainley_mathieson="ainley_mathieson"

class AnnulusStation(StrictModel):
    axial_m: float = Field(ge=0); hub_radius_m: float = Field(gt=0); shroud_radius_m: float = Field(gt=0)
    @model_validator(mode="after")
    def ordered(self):
        if self.shroud_radius_m <= self.hub_radius_m: raise ValueError("shroud radius must exceed hub radius")
        return self
class PassageGeometry(StrictModel):
    stations: List[AnnulusStation] = Field(min_length=2)
    @model_validator(mode="after")
    def ordered(self):
        x=[v.axial_m for v in self.stations]
        if any(b<=a for a,b in zip(x,x[1:])): raise ValueError("stations must have increasing axial_m")
        return self
class ProfilePoint(StrictModel):
    span_fraction: float = Field(ge=0,le=1); value: float
class RadialProfile(StrictModel):
    interpolation: Literal["linear"]="linear"; points: List[ProfilePoint]=Field(min_length=2)
    @model_validator(mode="after")
    def valid(self):
        s=[p.span_fraction for p in self.points]
        if s[0]!=0 or s[-1]!=1 or any(b<=a for a,b in zip(s,s[1:])): raise ValueError("profile must cover ordered span 0..1")
        return self
class BladeRow(StrictModel):
    row_id: str=Field(min_length=1); stage_id: Optional[str]=None; row_type: Literal["inlet","stator","rotor","outlet"]; axial_location_m: float=Field(ge=0)
    blade_count: Optional[int]=Field(default=None,ge=1); axial_chord_m: Optional[float]=Field(default=None,gt=0)
    tip_clearance_m: Optional[float]=Field(default=None,ge=0); metal_angle_in_deg: Optional[RadialProfile]=None; metal_angle_out_deg: Optional[RadialProfile]=None
    @model_validator(mode="after")
    def valid(self):
        blade=self.row_type in ("stator","rotor")
        if blade and (self.stage_id is None or self.blade_count is None or self.axial_chord_m is None): raise ValueError("blade rows require stage_id, blade_count and axial_chord_m")
        if not blade and (self.blade_count is not None or self.axial_chord_m is not None): raise ValueError("boundary rows cannot define blade geometry")
        if self.tip_clearance_m is not None and self.row_type!="rotor": raise ValueError("clearance is rotor-only")
        return self
class ThroughflowDesignV1(StrictModel):
    schema_version: Literal["throughflow_design_v1"]="throughflow_design_v1"; machine_type: Literal["turbine","compressor"]; flow_path: Literal["axial","radial","mixed"]
    passage: PassageGeometry; rows: List[BladeRow]=Field(min_length=3)
    @model_validator(mode="after")
    def topology(self):
        ids=[r.row_id for r in self.rows]; x=[r.axial_location_m for r in self.rows]
        if len(ids)!=len(set(ids)): raise ValueError("row_id values must be unique")
        if any(b<a for a,b in zip(x,x[1:])): raise ValueError("rows must be axially ordered")
        if self.rows[0].row_type!="inlet" or self.rows[-1].row_type!="outlet": raise ValueError("inlet/outlet boundaries required")
        stages=[r.stage_id for r in self.rows if r.row_type=="rotor"]
        if not stages or len(stages)!=len(set(stages)): raise ValueError("each stage requires exactly one rotor")
        return self
    @property
    def stage_count(self): return sum(r.row_type=="rotor" for r in self.rows)
class OperatingPoint(StrictModel):
    mass_flow_kg_s: float=Field(gt=0); inlet_total_pressure_pa: float=Field(gt=0); inlet_total_temperature_k: float=Field(gt=0); shaft_speed_rpm: float=Field(gt=0); inlet_mach: float=Field(default=.2,gt=0,lt=2); inlet_flow_angle_deg: float=0.0; outlet_static_pressure_pa: Optional[float]=Field(default=None,gt=0); outlet_total_pressure_pa: Optional[float]=Field(default=None,gt=0)
class SecondaryPoint(StrictModel):
    name: str=Field(min_length=1); mass_flow_kg_s: Optional[float]=Field(default=None,gt=0); shaft_speed_rpm: Optional[float]=Field(default=None,gt=0); outlet_static_pressure_pa: Optional[float]=Field(default=None,gt=0)
class Numerics(StrictModel):
    streamlines: int=Field(default=5,ge=1,le=65); max_iterations: int=Field(default=100,ge=1,le=2000); residual_tolerance: float=Field(default=1e-6,gt=0,le=1e-2); massflow_spread_tolerance: float=Field(default=.01,gt=0,le=.25)
LossModelName = Literal["fixed_pressure","diffusion","td2","kacker_okapuu","ainley_mathieson"]
class Physics(StrictModel):
    default_loss_model: LossModelName; row_loss_models: Dict[str,LossModelName]=Field(default_factory=dict); fixed_pressure_loss_fraction: Optional[float]=Field(default=None,ge=0,lt=1); row_fixed_pressure_loss_fractions: Dict[str,float]=Field(default_factory=dict)
    @model_validator(mode="after")
    def fixed(self):
        if any(not math.isfinite(v) or v<0 or v>=1 for v in self.row_fixed_pressure_loss_fractions.values()): raise ValueError("row fixed pressure loss fractions must be finite in [0,1)")
        selected={self.default_loss_model,*self.row_loss_models.values()}; has="fixed_pressure" in selected
        if not has and (self.fixed_pressure_loss_fraction is not None or self.row_fixed_pressure_loss_fractions): raise ValueError("fixed pressure loss fractions are unused")
        return self
class ThroughflowTaskV1(StrictModel):
    environment: Literal["turbomachinery_throughflow"]="turbomachinery_throughflow"; task_schema_version: Literal["throughflow_task_v1"]="throughflow_task_v1"
    simulator_version: Literal["nasa_turbo_design_experimental_v1"]="nasa_turbo_design_experimental_v1"; operating_conditions: OperatingPoint
    secondary_operating_points: List[SecondaryPoint]=Field(default_factory=list); physics: Physics; numerics: Numerics=Field(default_factory=Numerics); max_stages: int=Field(default=12,ge=1,le=30)
    def validate_design_ownership(self, design):
        if design.stage_count>self.max_stages: raise ValueError("design exceeds max_stages")
        row_ids={r.row_id for r in design.rows}; unknown=(set(self.physics.row_loss_models)|set(self.physics.row_fixed_pressure_loss_fractions))-row_ids
        if unknown: raise ValueError("loss models reference unknown rows: {}".format(sorted(unknown)))
        for row in design.rows:
            if row.row_type not in ("stator","rotor"): continue
            model=self.physics.row_loss_models.get(row.row_id,self.physics.default_loss_model)
            if model=="fixed_pressure" and row.row_id not in self.physics.row_fixed_pressure_loss_fractions and self.physics.fixed_pressure_loss_fraction is None: raise ValueError("fixed pressure loss requires a fraction for {}".format(row.row_id))
class Diagnostic(StrictModel):
    category: Literal["design_violation","model_validity","numerical_failure","infrastructure_failure","configuration_error"]
    code: str=Field(min_length=1); message: str=Field(min_length=1); location: Optional[str]=None
class ThroughflowSimulationResultV1(StrictModel):
    result_schema_version: Literal["throughflow_result_v1"]="throughflow_result_v1"; status: Literal["success","rejected","failed"]
    reward_eligible: bool=False; metrics: Dict[str,float]=Field(default_factory=dict); row_data: List[Dict[str,Any]]=Field(default_factory=list); stage_data: List[Dict[str,Any]]=Field(default_factory=list); span_data: List[Dict[str,Any]]=Field(default_factory=list); diagnostics: List[Diagnostic]=Field(default_factory=list); provenance: Dict[str,str]=Field(default_factory=dict)
    @model_validator(mode="after")
    def eligible(self):
        blocked={"numerical_failure","infrastructure_failure","configuration_error"}
        if self.reward_eligible and (self.status!="success" or any(d.category in blocked for d in self.diagnostics)): raise ValueError("reward eligibility requires clean success")
        return self
