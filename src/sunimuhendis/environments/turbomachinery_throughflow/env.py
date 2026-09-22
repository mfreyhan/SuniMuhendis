import math
from typing import Any, Dict
from pydantic import ValidationError
from ...core.base_environment import BaseEnvironment
from .contracts import ThroughflowDesignV1, ThroughflowTaskV1

class TurbomachineryThroughflowEnv(BaseEnvironment):
    def validate_schema(self, design_params: Dict[str, Any]):
        try: ThroughflowDesignV1.model_validate(design_params); return True,None
        except ValidationError as exc: return False,"Schema Error: {}".format(exc)
    def run_drc(self, design_params: Dict[str, Any]):
        design=ThroughflowDesignV1.model_validate(design_params)
        stations=design.passage.stations
        x_min,x_max=stations[0].axial_m,stations[-1].axial_m
        previous_exit=x_min
        for row in design.rows:
            if not x_min<=row.axial_location_m<=x_max:
                return False,"DRC Error: row {} lies outside the passage".format(row.row_id)
            if row.row_type not in ("stator","rotor"):
                continue
            leading_edge=row.axial_location_m-row.axial_chord_m
            if leading_edge<previous_exit-1e-12:
                return False,"DRC Error: blade row {} overlaps the preceding row".format(row.row_id)
            previous_exit=row.axial_location_m
            if any(abs(angle)>=89.0 for angle in row.metal_angle_in_deg+row.metal_angle_out_deg):
                return False,"DRC Error: row {} metal angles must remain below 89 degrees".format(row.row_id)
            if row.stagger_angle_deg is not None and any(abs(angle)>=85.0 for angle in row.stagger_angle_deg):
                return False,"DRC Error: row {} stagger angles must remain below 85 degrees".format(row.row_id)
            if row.trailing_edge_thickness_m is not None and row.trailing_edge_thickness_m>=0.2*row.axial_chord_m:
                return False,"DRC Error: row {} trailing edge is at least 20% of axial chord".format(row.row_id)
            hub=self._interpolate_station(stations,row.axial_location_m,"hub_radius_m")
            shroud=self._interpolate_station(stations,row.axial_location_m,"shroud_radius_m")
            span=shroud-hub
            if row.tip_clearance_m is not None and row.tip_clearance_m>=0.1*span:
                return False,"DRC Error: row {} tip clearance is at least 10% of span".format(row.row_id)
            if row.stagger_angle_deg is not None:
                mean_radius=0.5*(hub+shroud); pitch=2*math.pi*mean_radius/row.blade_count
                chord=max(row.axial_chord_m/abs(math.cos(math.radians(angle))) for angle in row.stagger_angle_deg)
                solidity=chord/pitch
                if not 0.2<=solidity<=4.0:
                    return False,"DRC Error: row {} mean solidity {:.3f} is outside [0.2, 4.0]".format(row.row_id,solidity)
        return True,None

    @staticmethod
    def _interpolate_station(stations,x,name):
        for left,right in zip(stations,stations[1:]):
            if left.axial_m<=x<=right.axial_m:
                fraction=(x-left.axial_m)/(right.axial_m-left.axial_m)
                return getattr(left,name)+fraction*(getattr(right,name)-getattr(left,name))
        return getattr(stations[-1],name)
    def prepare_simulation_inputs(self, design_params: Dict[str, Any], task_params: Dict[str, Any]):
        task=ThroughflowTaskV1.model_validate(task_params); design=ThroughflowDesignV1.model_validate(design_params); task.validate_design_ownership(design)
        return {"design":design.model_dump(mode="json"),"task":task.model_dump(mode="json")}
