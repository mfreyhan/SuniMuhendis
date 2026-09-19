import math
import random
from typing import Dict, Any, List, Optional, Sequence

import ht
from pydantic import ValidationError

from ...core.base_environment import BaseEnvironment
from ...core.base_score import BaseScoreFunction
from ...core.types import Requirement
from .schema import HeatExchangerDesign
from .drc import run_heat_exchanger_drc
from .simulator import HeatExchangerSimulator


class HeatExchangerEnv(BaseEnvironment):
    def validate_schema(self, design_params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        try:
            HeatExchangerDesign.model_validate(design_params)
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

    # ─────────────────────────────────────────────────────────────────
    #  Task feasibility audit hooks
    # ─────────────────────────────────────────────────────────────────

    #: Tube outside diameters in common commercial use [m] — 3/8" to 2".
    TUBE_OD_SERIES = (0.00953, 0.0127, 0.01588, 0.01905, 0.0254, 0.0318, 0.0381, 0.0508)

    #: Tube counts spanning small bundles to large ones. Even, because the
    #: DRC requires the count to divide by the (fixed) two tube passes.
    TUBE_COUNT_SERIES = (2, 4, 10, 20, 50, 100, 200, 400, 800, 1600)

    def sample_designs(self, num_samples: int, seed: int = 0) -> List[Dict[str, Any]]:
        """
        Spread candidate designs across the heat-exchanger design space.

        Deliberately broad rather than good: the audit asks what the task makes
        reachable, so a sampler that steered towards known-good designs would
        hide the very walls it is there to find. One design in ten is a
        concentric tube, which is the only way to reach pure counter-flow and
        therefore the only escape from the 1-2 shell-and-tube ε ceiling.

        Self-contained by design — ``baselines/`` is excluded from the wheel,
        so the shipped environment cannot depend on the samplers that live there.
        """
        rng = random.Random(seed)
        designs: List[Dict[str, Any]] = []
        for _ in range(num_samples):
            if rng.random() < 0.10:
                do = rng.uniform(0.01, 0.30)
                length = rng.uniform(1.0, 200.0)
                designs.append({
                    "geometry_type": "concentric_tube",
                    "length": length,
                    "inner_tube_di": do * rng.uniform(0.55, 0.95),
                    "inner_tube_do": do,
                    "outer_shell_di": do * rng.uniform(1.05, 4.0),
                    "number_of_tubes": 1,
                    "baffle_spacing": length / 5.0,
                })
                continue

            do = rng.choice(self.TUBE_OD_SERIES)
            length = rng.uniform(0.5, 15.0)
            designs.append({
                "geometry_type": "shell_and_tube",
                "length": length,
                "inner_tube_di": do * rng.uniform(0.55, 0.94),
                "inner_tube_do": do,
                "outer_shell_di": rng.uniform(0.1, 1.5),
                "number_of_tubes": rng.choice(self.TUBE_COUNT_SERIES),
                "baffle_spacing": rng.uniform(0.05, min(length * 0.95, 2.0)),
            })
        return designs

    def get_requirements(self, task_params: Dict[str, Any]) -> List[Requirement]:
        """
        The three hard requirements a heat-exchanger task imposes: deliver the
        target duty, and stay inside both pressure-drop limits.

        Defaults match those in ``score.py`` so an under-specified task audits
        the same way it scores.
        """
        return [
            Requirement(
                name="heat duty",
                metric_key="heat_duty_W",
                operator="gte",
                limit=float(task_params.get("target_heat_duty", 150000.0)),
            ),
            Requirement(
                name="tube pressure drop",
                metric_key="dp_tube_Pa",
                operator="lte",
                limit=float(task_params.get("max_dp_tube", 50000.0)),
            ),
            Requirement(
                name="shell pressure drop",
                metric_key="dp_shell_Pa",
                operator="lte",
                limit=float(task_params.get("max_dp_shell", 50000.0)),
            ),
        ]

    def list_design_checks(self) -> Sequence[str]:
        """
        Every check ``HeatExchangerSimulator._check_design_limits`` can raise,
        identified by a phrase unique to its warning text. Supplying this lets
        the audit report checks that never fire — rules that, as configured,
        protect nothing.
        """
        return (
            "erosion risk",
            "fouling risk",
            "Shell velocity # m/s > max",
            "Hot nozzle velocity",
            "Cold nozzle velocity",
            "Tube ΔP",
            "Shell ΔP",
            "Min approach",
            "poor design",
            "Tube wall",
            "Shell wall",
            "flow-induced vibration",
            "Unsupported span",
            "tube sag risk",
            "poor distribution",
            "TEMA minimum",
            "laminar flow",
            "transitional flow",
        )

    def analyse_physics(self, task_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Closed-form limits that sampling cannot prove, for this environment.

        Three walls a heat-exchanger task can be calibrated into:

        1. **The ε ceiling.** The schema fixes the configuration at one shell
           pass and two tube passes, whose effectiveness asymptotes to
           ``2/(1+Cr+√(1+Cr²))`` however much area a design buys. A duty target
           near that ceiling leaves nothing to optimise.
        2. **Duty that forces the F warning.** With flows and inlet temperatures
           fixed, the LMTD correction factor F depends on duty alone. Past a
           certain duty every design trips ``MIN_F_LMTD``, so meeting the
           requirement guarantees the penalty.
        3. **A pressure-drop budget eaten by the nozzles.** Nozzle diameter is
           not in the schema, so its loss is a constant the design cannot
           influence. When it dominates the limit, the real constraint is far
           tighter than the stated one — and can make the minimum tube velocity
           unreachable.
        """
        sim = HeatExchangerSimulator
        hot, cold = sim.HOT_FLUID, sim.COLD_FLUID

        c_hot = sim.DEFAULT_M_DOT_HOT * hot["Cp"]
        c_cold = sim.DEFAULT_M_DOT_COLD * cold["Cp"]
        c_min, c_max = min(c_hot, c_cold), max(c_hot, c_cold)
        c_ratio = c_min / c_max
        t_hot_in, t_cold_in = sim.DEFAULT_T_HOT_IN_C, sim.DEFAULT_T_COLD_IN_C
        duty_max = c_min * (t_hot_in - t_cold_in)

        # 1. ε ceiling of the 1-2 shell-and-tube configuration the schema forces.
        root = math.sqrt(1.0 + c_ratio ** 2)
        eps_ceiling = 2.0 / (1.0 + c_ratio + root)
        duty_ceiling = eps_ceiling * duty_max

        target = float(task_params.get("target_heat_duty", 150000.0))
        out: Dict[str, Any] = {
            "capacity_ratio_Cr": round(c_ratio, 5),
            "duty_max_thermodynamic_W": round(duty_max, 1),
            "epsilon_ceiling_1_2_shell_and_tube": round(eps_ceiling, 6),
            "duty_ceiling_1_2_shell_and_tube_W": round(duty_ceiling, 1),
            "target_duty_W": target,
        }

        reach = target / duty_ceiling if duty_ceiling > 0 else float("inf")
        out["target_as_fraction_of_duty_ceiling"] = round(reach, 4)
        if reach > 1.0:
            out["CRITICAL_duty_unreachable"] = (
                "target duty {:.0f} W exceeds the {:.0f} W ceiling of the 1-2 shell-and-tube "
                "configuration the schema forces; no design can meet it at any size"
                .format(target, duty_ceiling)
            )
        elif reach > 0.90:
            out["CRITICAL_duty_near_ceiling"] = (
                "target duty is {:.1%} of the {:.0f} W configuration ceiling — beyond NTU~3 more "
                "area buys almost no duty, so the heat objective is a threshold, not a gradient"
                .format(reach, duty_ceiling)
            )

        # 2. The duty past which every design trips the F correction warning.
        duty_at_f_limit = self._duty_at_f_limit(c_hot, c_cold, t_hot_in, t_cold_in, duty_ceiling)
        if duty_at_f_limit is not None:
            out["duty_at_F_limit_W"] = round(duty_at_f_limit, 1)
            if target > duty_at_f_limit:
                out["CRITICAL_F_warning_forced"] = (
                    "F falls below {} above {:.0f} W, and F depends on duty alone — so meeting the "
                    "{:.0f} W target guarantees the 'poor design' warning on every design"
                    .format(sim.MIN_F_LMTD, duty_at_f_limit, target)
                )

        # 3. Nozzle share of each pressure-drop budget, and the tube velocity it allows.
        limits = (
            ("tube", float(task_params.get("max_dp_tube", 50000.0)),
             hot["rho"], sim.DEFAULT_M_DOT_HOT, sim.DEFAULT_D_NOZZLE_HOT),
            ("shell", float(task_params.get("max_dp_shell", 50000.0)),
             cold["rho"], sim.DEFAULT_M_DOT_COLD, sim.DEFAULT_D_NOZZLE_COLD),
        )
        for side, limit, rho, m_dot, d_nozzle in limits:
            v_nozzle = m_dot / (rho * math.pi * (d_nozzle / 2.0) ** 2)
            dp_nozzle = sim.NOZZLE_K_TOTAL * rho * v_nozzle ** 2 / 2.0
            share = dp_nozzle / limit if limit > 0 else float("inf")
            out["{}_nozzle_dp_Pa".format(side)] = round(dp_nozzle, 1)
            out["{}_nozzle_share_of_limit".format(side)] = round(share, 4)
            if share >= 0.5:
                out["WARNING_{}_budget_is_fixed".format(side)] = (
                    "{:.0%} of the {:.0f} Pa {}-side limit is nozzle loss, which the schema does "
                    "not expose — the design can only influence the remaining {:.0f} Pa"
                    .format(share, limit, side, max(limit - dp_nozzle, 0.0))
                )

        # The tube-side budget left over caps velocity through the header loss alone.
        dp_tube_limit = float(task_params.get("max_dp_tube", 50000.0))
        v_nozzle_hot = sim.DEFAULT_M_DOT_HOT / (
            hot["rho"] * math.pi * (sim.DEFAULT_D_NOZZLE_HOT / 2.0) ** 2)
        budget = dp_tube_limit - sim.NOZZLE_K_TOTAL * hot["rho"] * v_nozzle_hot ** 2 / 2.0
        # Header loss is 4 velocity heads per pass; two passes are forced by the schema.
        header_coefficient = 4.0 * 2 * hot["rho"] / 2.0
        v_cap = math.sqrt(budget / header_coefficient) if budget > 0 else 0.0
        out["tube_velocity_cap_m_s"] = round(v_cap, 4)
        if v_cap < sim.MIN_TUBE_VELOCITY:
            out["CRITICAL_tube_velocity_warning_forced"] = (
                "the {:.0f} Pa tube limit caps velocity at {:.3f} m/s even with zero friction, "
                "below the {} m/s fouling minimum — so satisfying the pressure-drop requirement "
                "guarantees the velocity warning"
                .format(dp_tube_limit, v_cap, sim.MIN_TUBE_VELOCITY)
            )

        return out

    @staticmethod
    def _duty_at_f_limit(c_hot, c_cold, t_hot_in_c, t_cold_in_c, duty_ceiling):
        """
        The duty at which F crosses ``MIN_F_LMTD``, by bisection.

        F is a function of the four terminal temperatures; with flows and both
        inlets fixed, duty determines all of them, so F is a function of duty
        alone and crosses the limit exactly once (it falls monotonically as the
        temperature cross deepens). Returns None if the limit is never crossed
        below the configuration's duty ceiling.
        """
        limit = HeatExchangerSimulator.MIN_F_LMTD
        t_hot_in = t_hot_in_c + 273.15
        t_cold_in = t_cold_in_c + 273.15

        def f_at(duty):
            try:
                return ht.F_LMTD_Fakheri(
                    Thi=t_hot_in,
                    Tho=t_hot_in - duty / c_hot,
                    Tci=t_cold_in,
                    Tco=t_cold_in + duty / c_cold,
                    shells=1,
                )
            except (ValueError, ZeroDivisionError):
                return 0.0

        low, high = 1.0, duty_ceiling * 0.999
        if f_at(high) > limit:
            return None
        for _ in range(80):
            mid = (low + high) / 2.0
            if f_at(mid) > limit:
                low = mid
            else:
                high = mid
        return low
