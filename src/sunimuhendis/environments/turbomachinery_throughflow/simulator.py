"""Lazy adapter from SuniMuhendis contracts to NASA turbo-design."""
import math
from typing import Any, Dict, Tuple
from ...core.base_simulator import BaseSimulator
from .contracts import ThroughflowDesignV1, ThroughflowTaskV1

class NasaTurboDesignSimulator(BaseSimulator):
    VERSION = "nasa_turbo_design_experimental_v1"

    def simulate(self, inputs: Dict[str, Any]) -> Tuple[bool, Dict[str, float], Dict[str, Any], str]:
        try:
            design=ThroughflowDesignV1.model_validate(inputs["design"])
            task=ThroughflowTaskV1.model_validate(inputs["task"])
            task.validate_design_ownership(design)
            if design.machine_type != "turbine" or design.flow_path != "axial":
                raise ValueError("experimental backend currently supports axial turbines only")
            return self._solve_turbine(design, task)
        except (ImportError, ModuleNotFoundError) as exc:
            return False, {}, {}, "NASA turbo-design dependency is unavailable: {}".format(exc)
        except Exception as exc:
            return False, {}, {}, "NASA turbo-design solve failed: {}: {}".format(type(exc).__name__, exc)

    @staticmethod
    def _profile(profile, fallback):
        return [point.value for point in profile.points] if profile is not None else [fallback]

    def _loss(self, name, fraction):
        if name == "fixed_pressure":
            from turbodesign.loss import FixedPressureLoss
            return FixedPressureLoss(fraction)
        if name == "diffusion":
            from turbodesign.loss.compressor import DiffusionLoss
            return DiffusionLoss()
        if name == "td2":
            from turbodesign.loss.turbine import TD2
            return TD2()
        if name == "kacker_okapuu":
            from turbodesign.loss.turbine import KackerOkapuu
            return KackerOkapuu()
        if name == "ainley_mathieson":
            from turbodesign.loss.turbine import AinleyMathieson
            return AinleyMathieson()
        raise ValueError("unsupported loss model {}".format(name))

    def _solve_turbine(self, design, task):
        import numpy as np
        from cantera import Solution
        from turbodesign import Inlet, Outlet, Passage, PassageType, TurbineSpool
        from turbodesign.row_factory import make_rotor_row, make_stator_row

        stations=design.passage.stations
        x=np.asarray([s.axial_m for s in stations],dtype=float)
        passage=Passage(x,np.asarray([s.hub_radius_m for s in stations]),x,np.asarray([s.shroud_radius_m for s in stations]),passageType=PassageType.Axial)
        op=task.operating_conditions
        inlet=Inlet(hub_location=0,alpha=[0])
        inlet.init_total(P0=[op.inlet_total_pressure_pa],T0=[op.inlet_total_temperature_k],M=[0.2],percent_radii=[0.5])
        if op.outlet_static_pressure_pa is None:
            raise ValueError("axial turbine requires outlet_static_pressure_pa")
        outlet=Outlet(num_streamlines=task.numerics.streamlines)
        outlet.init_static(P=op.outlet_static_pressure_pa,percent_radii=[0.5])
        length=float(x[-1]-x[0]); rows=[]; row_map={}
        stage_names=list(dict.fromkeys(row.stage_id for row in design.rows if row.row_type=="rotor"))
        stage_index={name:index for index,name in enumerate(stage_names)}
        for row in design.rows[1:-1]:
            location=(row.axial_location_m-x[0])/length
            loss_name=task.physics.row_loss_models.get(row.row_id,task.physics.default_loss_model)
            loss=self._loss(loss_name,task.physics.fixed_pressure_loss_fraction or 0.0)
            angles=self._profile(row.metal_angle_out_deg,70.0 if row.row_type=="stator" else -65.0)
            built=(make_stator_row if row.row_type=="stator" else make_rotor_row)(hub_location=location,metal_exit_angle_deg=angles,loss_function=loss)
            built.stage_id=stage_index[row.stage_id]
            built.axial_chord=row.axial_chord_m
            rows.append(built); row_map[row.row_id]=built
        fluid=Solution("air.yaml"); fluid.TP=op.inlet_total_temperature_k,op.inlet_total_pressure_pa
        spool=TurbineSpool(passage=passage,massflow=op.mass_flow_kg_s,inlet=inlet,outlet=outlet,rows=rows,rpm=op.shaft_speed_rpm,num_streamlines=task.numerics.streamlines,fluid=fluid)
        spool.adjust_streamlines=False
        spool.solve()
        metrics={"power_W":float(spool.total_power()),"pressure_ratio_total":float(spool.overall_pressure_ratio()),"efficiency_polytropic":float(spool.overall_polytropic_efficiency()),"stage_count":float(design.stage_count),"streamline_count":float(task.numerics.streamlines)}
        if not all(math.isfinite(v) for v in metrics.values()): raise ValueError("solver returned non-finite summary metrics")
        raw={"backend":"nasa/turbo-design","backend_mode":"fixed_streamline_geometry","simulator_version":self.VERSION,"convergence_history":getattr(spool,"convergence_history",[]),"rows":[{"row_id":key,"P0":np.asarray(getattr(value,"P0",[])).tolist(),"T0":np.asarray(getattr(value,"T0",[])).tolist(),"M":np.asarray(getattr(value,"M",[])).tolist()} for key,value in row_map.items()]}
        return True,metrics,raw,""
