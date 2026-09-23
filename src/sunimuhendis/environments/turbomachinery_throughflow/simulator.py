"""Lazy adapter from SuniMuhendis contracts to NASA turbo-design."""
import math
from typing import Any, Dict, Tuple
from ...core.base_simulator import BaseSimulator
from .assets import require_nasa_asset
from .contracts import ThroughflowDesignV1, ThroughflowTaskV1
from .physics import CorrectedCarterDeviation, MeanlineGeometryLossAdapter, SeededLossAdapter
from .profiles import get_physics_profile

class NasaTurboDesignSimulator(BaseSimulator):
    VERSION = "nasa_turbo_design_experimental_v2"

    def simulate(self, inputs: Dict[str, Any]) -> Tuple[bool, Dict[str, float], Dict[str, Any], str]:
        try:
            design=ThroughflowDesignV1.model_validate(inputs["design"])
            task=ThroughflowTaskV1.model_validate(inputs["task"])
            task.validate_design_ownership(design)
            if design.flow_path != "axial": raise ValueError("experimental backend currently supports axial machines only")
            return self._solve_turbine(design, task) if design.machine_type=="turbine" else self._solve_compressor(design,task)
        except (ImportError, ModuleNotFoundError) as exc:
            return False, {}, {}, "NASA turbo-design dependency is unavailable: {}".format(exc)
        except Exception as exc:
            return False, {}, {}, "NASA turbo-design solve failed: {}: {}".format(type(exc).__name__, exc)

    def _loss(self, name, fraction):
        if name == "fixed_pressure":
            from turbodesign.loss import FixedPressureLoss
            return FixedPressureLoss(fraction)
        if name == "diffusion":
            from turbodesign.loss.compressor import DiffusionLoss
            return DiffusionLoss()
        if name == "td2":
            from turbodesign.loss.turbine import TD2
            return SeededLossAdapter(TD2())
        if name == "kacker_okapuu":
            require_nasa_asset("kackerokapuu.pkl")
            from turbodesign.loss.turbine import KackerOkapuu
            return MeanlineGeometryLossAdapter(KackerOkapuu())
        if name == "ainley_mathieson":
            require_nasa_asset("ainleymathieson.pkl")
            from turbodesign.loss.turbine import AinleyMathieson
            return AinleyMathieson()
        raise ValueError("unsupported loss model {}".format(name))

    def _deviation(self, name, values=None):
        if name == "zero":
            return None
        if name == "fixed":
            from turbodesign.deviation import FixedDeviation
            return FixedDeviation(values)
        if name == "carter":
            return CorrectedCarterDeviation()
        raise ValueError("unsupported deviation model {}".format(name))

    @staticmethod
    def _configure_candidate_geometry(built, row, stations):
        """Transfer loss/deviation-relevant geometry into the NASA row."""
        import numpy as np

        if row.stagger_angle_deg is not None:
            built.stagger = np.asarray(row.stagger_angle_deg, dtype=float)

        x = np.asarray([station.axial_m for station in stations], dtype=float)
        hub = float(np.interp(row.axial_location_m, x, [s.hub_radius_m for s in stations]))
        shroud = float(np.interp(row.axial_location_m, x, [s.shroud_radius_m for s in stations]))
        span = shroud - hub
        if row.tip_clearance_m is not None:
            built.tip_clearance = row.tip_clearance_m / span
        if row.trailing_edge_thickness_m is not None:
            mean_radius = 0.5 * (hub + shroud)
            mean_pitch = 2.0 * math.pi * mean_radius / row.blade_count
            built.te_pitch = row.trailing_edge_thickness_m / mean_pitch

    @staticmethod
    def _finalize_candidate_geometry(row_map, design):
        """Restore the design's stagger and derive local solidity after NASA setup."""
        import numpy as np

        design_rows = {row.row_id: row for row in design.rows}
        for row_id, built in row_map.items():
            source = design_rows[row_id]
            span = np.asarray(built.percent_hub_shroud, dtype=float)
            stagger = np.interp(
                span,
                np.linspace(0.0, 1.0, len(source.stagger_angle_deg)),
                source.stagger_angle_deg,
            )
            chord = source.axial_chord_m / np.maximum(
                np.abs(np.cos(np.radians(stagger))), 1e-6
            )
            pitch = 2.0 * math.pi * np.asarray(built.r, dtype=float) / source.blade_count
            built._stagger = stagger
            built._pitch_to_chord = pitch / chord

    @staticmethod
    def _row_output(row_id, built, loss_name, deviation_name):
        import numpy as np

        def values(name, degrees=False):
            result = np.asarray(getattr(built, name, []), dtype=float)
            if degrees:
                result = np.degrees(result)
            return result.tolist()

        return {
            "row_id": row_id,
            "loss_model": loss_name,
            "deviation_model": deviation_name,
            "P0": values("P0"),
            "T0": values("T0"),
            "M": values("M"),
            "M_rel": values("M_rel"),
            "Yp": values("Yp"),
            "solidity": values("solidity"),
            "deviation_deg": values("deviation", degrees=True),
            "flow_angle_absolute_deg": values("alpha2", degrees=True),
            "flow_angle_relative_deg": values("beta2", degrees=True),
            "metal_angle_in_deg": values("beta1_metal"),
            "metal_angle_out_deg": values("beta2_metal"),
            "tip_clearance_fraction": float(getattr(built, "tip_clearance", 0.0)),
            "trailing_edge_to_pitch": float(getattr(built, "te_pitch", 0.0)),
        }

    @staticmethod
    def _fidelity_notes(task):
        notes = []
        if task.physics_profile == "axial_compressor_candidate_v1":
            notes.append(
                "NASA DiffusionLoss is a preliminary diffusion-factor model and does not include a separate incidence-loss correlation."
            )
            notes.append(
                "The pinned DiffusionLoss uses rotor speed in its loading term; for stators U=0, so ordinary de-swirl commonly clips the predicted stator loss to zero. Treat this profile as a solver demonstration, not a validated loss prediction."
            )
            notes.append(
                "Carter deviation uses the corrected documented algebra because the pinned NASA class has a radians/degrees interface mismatch."
            )
        if task.physics_profile == "axial_turbine_candidate_v1":
            notes.append(
                "NASA TD2 is an interim initial-estimate correlation; the more detailed Kacker-Okapuu path is blocked by known initialization and stator secondary-loss defects in the pinned backend."
            )
            if task.physics.default_deviation_model == "zero":
                notes.append(
                    "No general turbine deviation correlation is available in the pinned backend; exit flow follows exit metal angle unless calibrated fixed deviation is supplied."
                )
        return notes

    @staticmethod
    def _compressor_convergence(spool, task):
        """Return dimensionless convergence evidence and reject loose solves."""
        history = list(getattr(spool, "convergence_history", []) or [])
        if not history:
            raise RuntimeError("compressor solver returned no convergence history")
        final_std = float(history[-1]["massflow_std"])
        massflow = float(task.operating_conditions.mass_flow_kg_s)
        residual = final_std / massflow
        rows = spool._all_rows()[1:-1]
        row_flows = [
            float(row.total_massflow_no_coolant)
            for row in rows
            if hasattr(row, "total_massflow_no_coolant")
        ]
        spread = (max(row_flows) - min(row_flows)) / massflow if row_flows else 0.0
        if residual > task.numerics.residual_tolerance:
            raise RuntimeError(
                "compressor massflow residual {:.3e} exceeds tolerance {:.3e}".format(
                    residual, task.numerics.residual_tolerance
                )
            )
        if spread > task.numerics.massflow_spread_tolerance:
            raise RuntimeError(
                "compressor row massflow spread {:.3e} exceeds tolerance {:.3e}".format(
                    spread, task.numerics.massflow_spread_tolerance
                )
            )
        return {
            "massflow_residual": residual,
            "massflow_row_spread": spread,
            "solver_iterations": float(len(history)),
        }

    def _solve_turbine(self, design, task):
        import numpy as np
        from cantera import Solution
        from turbodesign import Inlet, Outlet, Passage, PassageType, TurbineSpool
        from turbodesign.row_factory import make_rotor_row, make_stator_row

        stations=design.passage.stations
        x=np.asarray([s.axial_m for s in stations],dtype=float)
        passage=Passage(x,np.asarray([s.hub_radius_m for s in stations]),x,np.asarray([s.shroud_radius_m for s in stations]),passageType=PassageType.Axial)
        op=task.operating_conditions
        inlet=Inlet(hub_location=0,alpha=[op.inlet_flow_angle_deg])
        inlet.init_total(P0=[op.inlet_total_pressure_pa],T0=[op.inlet_total_temperature_k],M=[op.inlet_mach],percent_radii=[0.5])
        if op.outlet_static_pressure_pa is None:
            raise ValueError("axial turbine requires outlet_static_pressure_pa")
        outlet=Outlet(num_streamlines=task.numerics.streamlines)
        outlet.init_static(P=op.outlet_static_pressure_pa,percent_radii=[0.5])
        length=float(x[-1]-x[0]); rows=[]; row_map={}; row_physics={}
        profile=get_physics_profile(task.physics_profile)
        stage_names=list(dict.fromkeys(row.stage_id for row in design.rows if row.row_type=="rotor"))
        stage_index={name:index for index,name in enumerate(stage_names)}
        for row in design.rows[1:-1]:
            location=(row.axial_location_m-x[0])/length
            loss_name=task.physics.row_loss_models.get(row.row_id,task.physics.default_loss_model)
            fraction=task.physics.row_fixed_pressure_loss_fractions.get(row.row_id,task.physics.fixed_pressure_loss_fraction or 0.0)
            loss=self._loss(loss_name,fraction)
            built=(make_stator_row if row.row_type=="stator" else make_rotor_row)(hub_location=location,metal_exit_angle_deg=row.metal_angle_out_deg,loss_function=loss,num_blades=row.blade_count,axial_chord=row.axial_chord_m)
            built.metal_inlet_angle=row.metal_angle_in_deg
            deviation_name=task.physics.row_deviation_models.get(row.row_id,task.physics.default_deviation_model)
            built.deviation_function=self._deviation(deviation_name,task.physics.row_fixed_deviation_deg.get(row.row_id))
            if profile.requires_complete_blade_geometry:
                self._configure_candidate_geometry(built,row,stations)
            built.stage_id=stage_index[row.stage_id]
            rows.append(built); row_map[row.row_id]=built; row_physics[row.row_id]=(loss_name,deviation_name)
        fluid=Solution("air.yaml"); fluid.TP=op.inlet_total_temperature_k,op.inlet_total_pressure_pa
        spool=TurbineSpool(passage=passage,massflow=op.mass_flow_kg_s,inlet=inlet,outlet=outlet,rows=rows,rpm=op.shaft_speed_rpm,num_streamlines=task.numerics.streamlines,fluid=fluid)
        spool.adjust_streamlines=False
        if profile.requires_complete_blade_geometry:
            spool.initialize_streamlines()
            self._finalize_candidate_geometry(row_map,design)
            spool.initialize()
            spool._balance_pressure()
        else:
            spool.solve()
        metrics={"power_W":float(spool.total_power()),"pressure_ratio_total":float(spool.overall_pressure_ratio()),"efficiency_polytropic":float(spool.overall_polytropic_efficiency()),"stage_count":float(design.stage_count),"streamline_count":float(task.numerics.streamlines),"streamtube_count":float(task.numerics.streamlines-1)}
        if not all(math.isfinite(v) for v in metrics.values()): raise ValueError("solver returned non-finite summary metrics")
        raw={"backend":"nasa/turbo-design","backend_mode":"fixed_streamline_geometry","simulator_version":self.VERSION,"physics_profile":profile.provenance(),"convergence_history":getattr(spool,"convergence_history",[]),"fidelity_notes":self._fidelity_notes(task),"rows":[self._row_output(key,value,*row_physics[key]) for key,value in row_map.items()]}
        return True,metrics,raw,""

    def _solve_compressor(self,design,task):
        import numpy as np
        from cantera import Solution
        from turbodesign import Inlet,Outlet,Passage,PassageType
        from turbodesign.compressor_spool import CompressorSpool
        from turbodesign.row_factory import make_rotor_row,make_stator_row
        stations=design.passage.stations; x=np.asarray([s.axial_m for s in stations],dtype=float)
        passage=Passage(x,np.asarray([s.hub_radius_m for s in stations]),x,np.asarray([s.shroud_radius_m for s in stations]),passageType=PassageType.Axial,zero_phi=True)
        op=task.operating_conditions
        if op.outlet_total_pressure_pa is None: raise ValueError("axial compressor requires outlet_total_pressure_pa")
        inlet=Inlet(hub_location=0,alpha=[op.inlet_flow_angle_deg]); inlet.init_total([op.inlet_total_pressure_pa],[op.inlet_total_temperature_k],M=[op.inlet_mach],percent_radii=[.5])
        outlet=Outlet(num_streamlines=task.numerics.streamlines); outlet.init_total(op.outlet_total_pressure_pa,[.5])
        length=float(x[-1]-x[0]); rows=[]; row_map={}; row_physics={}; stage_ratio=(op.outlet_total_pressure_pa/op.inlet_total_pressure_pa)**(1/design.stage_count)
        profile=get_physics_profile(task.physics_profile)
        stage_names=list(dict.fromkeys(r.stage_id for r in design.rows if r.row_type=="rotor")); stage_index={name:i for i,name in enumerate(stage_names)}
        for row in design.rows[1:-1]:
            location=(row.axial_location_m-x[0])/length; loss_name=task.physics.row_loss_models.get(row.row_id,task.physics.default_loss_model); fraction=task.physics.row_fixed_pressure_loss_fractions.get(row.row_id,task.physics.fixed_pressure_loss_fraction or 0.0); loss=self._loss(loss_name,fraction)
            factory=make_rotor_row if row.row_type=="rotor" else make_stator_row
            built=factory(hub_location=location,metal_exit_angle_deg=row.metal_angle_out_deg,loss_function=loss,P0_ratio=stage_ratio if row.row_type=="stator" else 1.0,num_blades=row.blade_count,axial_chord=row.axial_chord_m); built.metal_inlet_angle=row.metal_angle_in_deg; built.stage_id=stage_index[row.stage_id]; rows.append(built); row_map[row.row_id]=built
            deviation_name=task.physics.row_deviation_models.get(row.row_id,task.physics.default_deviation_model)
            built.deviation_function=self._deviation(deviation_name,task.physics.row_fixed_deviation_deg.get(row.row_id))
            if profile.requires_complete_blade_geometry:
                self._configure_candidate_geometry(built,row,stations)
            row_physics[row.row_id]=(loss_name,deviation_name)
        fluid=Solution("air.yaml"); fluid.TP=op.inlet_total_temperature_k,op.inlet_total_pressure_pa
        spool=CompressorSpool(passage,op.mass_flow_kg_s,inlet,outlet,rows,num_streamlines=task.numerics.streamlines,fluid=fluid,rpm=op.shaft_speed_rpm)
        spool.adjust_streamlines=False
        if profile.requires_complete_blade_geometry:
            spool.initialize_streamlines()
            self._finalize_candidate_geometry(row_map,design)
            spool.initialize()
            spool.balance_pressure()
        else:
            spool.solve_balance_pressure()
        pressure_ratio=float(spool.overall_pressure_ratio())
        target_pressure_ratio=op.outlet_total_pressure_pa/op.inlet_total_pressure_pa
        metrics={"power_W":float(spool.total_power()),"pressure_ratio_total":pressure_ratio,"target_pressure_ratio_total":target_pressure_ratio,"pressure_ratio_relative_error":abs(pressure_ratio-target_pressure_ratio)/target_pressure_ratio,"efficiency_polytropic":float(spool.overall_polytropic_efficiency()),"stage_count":float(design.stage_count),"streamline_count":float(task.numerics.streamlines),"streamtube_count":float(task.numerics.streamlines-1)}
        metrics.update(self._compressor_convergence(spool,task))
        if not all(math.isfinite(v) for v in metrics.values()): raise ValueError("solver returned non-finite summary metrics")
        if profile.maturity == "candidate" and not (0.0 < metrics["efficiency_polytropic"] <= 1.0):
            raise ValueError(
                "candidate compressor returned non-physical polytropic efficiency {:.6f}".format(
                    metrics["efficiency_polytropic"]
                )
            )
        raw={"backend":"nasa/turbo-design","backend_mode":"fixed_streamline_geometry","simulator_version":self.VERSION,"physics_profile":profile.provenance(),"convergence_history":getattr(spool,"convergence_history",[]),"fidelity_notes":self._fidelity_notes(task),"rows":[self._row_output(key,value,*row_physics[key]) for key,value in row_map.items()]}
        return True,metrics,raw,""
