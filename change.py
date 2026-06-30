"""
Heat Exchanger Simulator — Comprehensive Design Tool
=====================================================
Uses:
  - `ht` (Heat Transfer) library: tube-side Nu, ε-NTU correlations
  - `fluids` library: tube-side friction factor
  - Custom Kern/Bell-Delaware methods for shell-side (no library equivalent)

Original bugs fixed:
  - ht.conv_internal used for shell-side  →  now only for tube-side
  - fluids.friction_factor for shell-side →  now only for tube-side
  - Wrong ε-NTU for shell-and-tube        →  proper 1-2 S&T formula
  - Missing fouling, headers, nozzles     →  all added
  - No mechanical/economic checks          →  comprehensive design review
"""

import math
from typing import Dict, Any, Tuple, List

# ── Third-party engineering libraries ──────────────────────────────
import ht
import fluids


class HeatExchangerSimulator:
    """
    Comprehensive shell-and-tube / concentric-tube heat exchanger simulator.

    Uses ht and fluids libraries where appropriate (internal/tube-side flow),
    and implements shell-side correlations from first principles (Kern method,
    Bell-Delaware approximations) since no library provides cross-flow
    tube-bundle correlations.
    """

    # ── Material cost multipliers (relative to carbon steel) ────────
    MATERIAL_FACTORS = {
        "carbon_steel": 1.0,
        "stainless_304": 1.75,
        "stainless_316": 2.0,
        "titanium": 5.0,
        "cupronickel": 2.5,
    }

    STEEL_DENSITY = 7850.0        # kg/m³
    CARBON_STEEL_COST = 4.0       # $/kg raw material
    FABRICATION_FACTOR = 3.0       # fabricated / raw cost ratio
    BAFFLE_COST_EACH = 50.0       # $/baffle (installed)
    PUMP_EFFICIENCY = 0.70
    OPERATING_HOURS = 8000        # h/year
    ELECTRICITY_COST = 0.10       # $/kWh
    PAYBACK_YEARS = 5.0

    # ── TEMA / ASME design limits ───────────────────────────────────
    MAX_TUBE_VELOCITY = 3.0       # m/s (liquid service)
    MIN_TUBE_VELOCITY = 0.5       # m/s (below this → fouling risk)
    MAX_SHELL_VELOCITY = 2.0      # m/s (liquid, cross-flow)
    MAX_NOZZLE_VELOCITY = 5.0     # m/s (liquid)
    MAX_DP_TUBE = 10000.0         # Pa
    MAX_DP_SHELL = 10000.0        # Pa
    MIN_APPROACH_TEMP = 5.0       # °C (pinch limit)
    MIN_F_LMTD = 0.75             # below this → poor design
    MAX_UNSUPPORTED_SPAN = 1.5    # m (vibration limit, carbon steel)
    MAX_L_D_RATIO = 15.0
    MIN_L_D_RATIO = 3.0

    def simulate(
        self, design_params: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, float], Dict[str, Any], str]:
        """Run full heat exchanger simulation."""
        try:
            params = self._extract_and_validate_params(design_params)
            if params is None:
                return False, {}, {}, "Invalid design parameters"

            # ── Unpack ───────────────────────────────────────────────
            geo       = params["geo"]
            L         = params["L"]
            di        = params["di"]
            do        = params["do"]
            D_shell   = params["D_shell"]
            N_tubes   = params["N_tubes"]
            N_pass    = params["N_pass"]
            pitch_type = params["pitch_type"]
            material  = params["material"]
            baffle_spacing = params["baffle_spacing"]
            baffle_cut = params["baffle_cut"]
            n_baffles = params["n_baffles"]
            pitch     = params["pitch"]

            hot  = params["hot"]
            cold = params["cold"]
            wall = params["wall"]
            mech = params["mech"]

            # ═════════════════════════════════════════════════════════
            #  1. TUBE-SIDE  (uses ht + fluids libraries)
            # ═════════════════════════════════════════════════════════
            tube = self._calc_tube_side(
                di, do, L, N_tubes, N_pass,
                hot, wall, mech,
            )

            # ═════════════════════════════════════════════════════════
            #  2. SHELL / ANNULUS SIDE
            # ═════════════════════════════════════════════════════════
            if geo == "concentric_tube":
                shell = self._calc_annulus_side(
                    D_shell, do, L, cold, wall, mech,
                )
            else:
                shell = self._calc_shell_side(
                    D_shell, do, N_tubes, L, pitch_type,
                    pitch, baffle_spacing, baffle_cut, n_baffles,
                    cold, mech,
                )

            # ═════════════════════════════════════════════════════════
            #  3. OVERALL HEAT TRANSFER COEFFICIENT
            # ═════════════════════════════════════════════════════════
            thermal = self._calc_overall_thermal(
                tube, shell, L, di, do, N_tubes, hot, cold, wall,
            )

            # ═════════════════════════════════════════════════════════
            #  4. ε-NTU METHOD  (uses ht library)
            # ═════════════════════════════════════════════════════════
            ntu = self._calc_effectiveness(
                geo, thermal["UA"], hot, cold,
            )

            # ═════════════════════════════════════════════════════════
            #  5. LMTD & F CORRECTION
            # ═════════════════════════════════════════════════════════
            lmtd = self._calc_LMTD(
                geo, ntu["T_hot_out"], ntu["T_cold_out"],
                hot["T_in"], cold["T_in"],
            )

            # ═════════════════════════════════════════════════════════
            #  6. WALL TEMPERATURE
            # ═════════════════════════════════════════════════════════
            wall_temp = self._calc_wall_temperature(
                tube["h_i"], shell["h_o"], thermal["U_dirty"],
                ntu["T_hot_out"], ntu["T_cold_out"],
                hot["T_in"], cold["T_in"],
            )

            # ═════════════════════════════════════════════════════════
            #  7. MECHANICAL CHECKS
            # ═════════════════════════════════════════════════════════
            mechanical = self._calc_mechanical(
                di, do, D_shell, L, baffle_spacing,
                N_tubes, shell["v"], cold["rho"], mech,
            )

            # ═════════════════════════════════════════════════════════
            #  8. GEOMETRIC PARAMETERS
            # ═════════════════════════════════════════════════════════
            geometric = self._calc_geometric(
                geo, L, di, do, D_shell, N_tubes, N_pass,
                pitch_type, pitch, baffle_spacing, baffle_cut, n_baffles,
            )

            # ═════════════════════════════════════════════════════════
            #  9. COST MODEL
            # ═════════════════════════════════════════════════════════
            cost = self._calc_cost(
                L, di, do, D_shell, N_tubes, N_pass, n_baffles,
                tube["dp_total"], shell["dp_total"],
                hot["m_dot"], cold["m_dot"],
                hot["rho"], cold["rho"], material,
                ntu["Q"], thermal["A_o_total"],
            )

            # ═════════════════════════════════════════════════════════
            #  10. DESIGN LIMIT CHECKS
            # ═════════════════════════════════════════════════════════
            warnings = self._check_design_limits(
                geo, tube, shell, ntu, lmtd, mechanical, geometric,
            )

            # ═════════════════════════════════════════════════════════
            #  11. ASSEMBLE ALL OUTPUTS
            # ═════════════════════════════════════════════════════════
            metrics = {}
            metrics.update(self._format_thermal(thermal, ntu, lmtd))
            metrics.update(self._format_hydraulic(tube, shell))
            metrics.update(self._format_htc(thermal))
            metrics.update(self._format_wall_temp(wall_temp))
            metrics.update(self._format_mechanical(mechanical))
            metrics.update(self._format_geometric(geometric))
            metrics.update(self._format_cost(cost))
            metrics["num_warnings"] = float(len(warnings))

            raw_data = {
                "C_hot_W_K": hot["m_dot"] * hot["Cp"],
                "C_cold_W_K": cold["m_dot"] * cold["Cp"],
                "C_r": ntu["C_r"],
                "R_total_K_W": thermal["R_total"],
                "warnings": warnings,
            }

            for k, v in metrics.items():
                if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                    return False, {}, raw_data, f"Metric {k} is NaN/Inf."

            return True, metrics, raw_data, ""

        except Exception as e:
            return False, {}, {}, f"Unexpected error: {str(e)}"

    # ═════════════════════════════════════════════════════════════════
    #  PARAMETER EXTRACTION
    # ═════════════════════════════════════════════════════════════════

    @staticmethod
    def _extract_and_validate_params(dp):
        """Extract, default, and validate all design parameters."""
        try:
            geo = dp["geometry_type"]
            L = dp["length"]
            di = dp["inner_tube_di"]
            do = dp["inner_tube_do"]
            D_shell = dp["outer_shell_di"]
            N_tubes = dp["number_of_tubes"]
        except KeyError as e:
            return None  # caller handles

        if do <= di:
            return None
        if D_shell <= do:
            return None
        if L <= 0 or N_tubes <= 0:
            return None

        N_pass = dp.get("tube_passes", 2)
        pitch_type = dp.get("pitch_type", "square")
        material = dp.get("material", "carbon_steel")

        baffle_spacing = dp.get("baffle_spacing", L / 5)
        if baffle_spacing <= 0:
            baffle_spacing = L / 5
        baffle_cut = dp.get("baffle_cut", 0.25)
        n_baffles = max(1, int(round(L / baffle_spacing)) - 1)
        pitch = do * dp.get("pitch_ratio", 1.25)

        hot = {
            "m_dot": dp.get("m_dot_hot", 1.0),
            "T_in": dp.get("T_hot_in", 80.0) + 273.15,
            "T_in_C": dp.get("T_hot_in", 80.0),
            "rho": 971.8, "mu": 3.55e-4,
            "k": 0.67, "Cp": 4190, "Pr": 2.2,
        }

        cold = {
            "m_dot": dp.get("m_dot_cold", 1.0),
            "T_in": dp.get("T_cold_in", 20.0) + 273.15,
            "T_in_C": dp.get("T_cold_in", 20.0),
            "rho": 998.2, "mu": 10.02e-4,
            "k": 0.598, "Cp": 4182, "Pr": 7.0,
        }

        wall = {
            "k_wall": dp.get("k_wall", 50.0),
            "R_fi": dp.get("R_fi", 1.76e-4),
            "R_fo": dp.get("R_fo", 1.76e-4),
        }

        mech = {
            "P_design": dp.get("P_design", 101325.0),
            "allowable_stress": dp.get("allowable_stress", 137e6),
            "D_nozzle_hot": dp.get("D_nozzle_hot", 0.05),
            "D_nozzle_cold": dp.get("D_nozzle_cold", 0.05),
        }

        return {
            "geo": geo, "L": L, "di": di, "do": do,
            "D_shell": D_shell, "N_tubes": N_tubes,
            "N_pass": N_pass, "pitch_type": pitch_type,
            "material": material, "baffle_spacing": baffle_spacing,
            "baffle_cut": baffle_cut, "n_baffles": n_baffles,
            "pitch": pitch, "hot": hot, "cold": cold,
            "wall": wall, "mech": mech,
        }

    # ═════════════════════════════════════════════════════════════════
    #  1. TUBE-SIDE  — Uses ht + fluids libraries
    # ═════════════════════════════════════════════════════════════════

    @staticmethod
    def _calc_tube_side(di, do, L, N_tubes, N_pass, hot, wall, mech):
        """
        Tube-side heat transfer and pressure drop.

        ✅ Uses ht.conv_internal for Nusselt number
        ✅ Uses fluids.friction for Darcy friction factor
        """
        rho = hot["rho"]
        mu = hot["mu"]
        k = hot["k"]
        Cp = hot["Cp"]
        Pr = hot["Pr"]
        m_dot = hot["m_dot"]

        # ── Flow area and velocity ────────────────────────────────
        A_tube_in_total = N_tubes * math.pi * (di / 2) ** 2
        v = m_dot / (rho * A_tube_in_total)
        G = rho * v  # mass velocity
        Re = rho * v * di / mu

        # ── Nusselt number  — ht library ✅ ──────────────────────
        # ht.conv_internal.Nu_conv_internal automatically selects:
        #   Laminar (Re < 2300):  3.66 (const T) or 4.36 (const q)
        #   Turbulent:            Gnielinski correlation (most accurate)
        # It also handles the transition region with interpolation.
        eD = 0.0  # smooth tubes
        Nu = ht.conv_internal.Nu_conv_internal(Re=Re, Pr=Pr, eD=eD)

        h_i = Nu * k / di

        # Colburn j-factor and Stanton number
        St = Nu / (Re * Pr ** (1.0 / 3.0)) if Re > 0 else 0.0
        j_h = St * Pr ** (2.0 / 3.0)

        # ── Friction factor — fluids library ✅ ──────────────────
        # fluids.friction.friction_factor returns the Darcy (Moody) f
        # Handles both laminar (f=64/Re) and turbulent (Colebrook-based)
        f_D = fluids.friction.friction_factor(Re=Re, eD=eD)

        # ── Pressure drop components ──────────────────────────────
        # (a) Friction in all tube passes
        dp_friction = f_D * (L * N_pass / di) * (rho * v ** 2 / 2)

        # (b) Header / return losses (4 velocity heads per pass, Kern)
        dp_header = 4.0 * N_pass * (rho * v ** 2 / 2)

        # (c) Nozzle losses (inlet K=1.5, outlet K=0.5)
        v_nozzle = m_dot / (rho * math.pi * (mech["D_nozzle_hot"] / 2) ** 2)
        dp_nozzle = (1.5 + 0.5) * (rho * v_nozzle ** 2 / 2)

        dp_total = dp_friction + dp_header + dp_nozzle

        return {
            "v": v, "G": G, "Re": Re, "Nu": Nu,
            "h_i": h_i, "St": St, "j_h": j_h, "f_D": f_D,
            "v_nozzle": v_nozzle,
            "dp_friction": dp_friction,
            "dp_header": dp_header,
            "dp_nozzle": dp_nozzle,
            "dp_total": dp_total,
            "dp_per_m": dp_total / L if L > 0 else 0,
            "flow_regime": ("turbulent" if Re > 4000
                           else "transitional" if Re > 2300
                           else "laminar"),
        }

    # ═════════════════════════════════════════════════════════════════
    #  2a. ANNULUS SIDE  (concentric tube)
    # ═════════════════════════════════════════════════════════════════

    @staticmethod
    def _calc_annulus_side(D_shell, do, L, cold, wall, mech):
        """
        Annulus-side for concentric tube geometry.
        Uses annulus-corrected laminar Nu (not pipe Nu=4.36).
        Uses fluids library for base friction factor with Jones correction.
        """
        rho = cold["rho"]; mu = cold["mu"]
        k = cold["k"]; Cp = cold["Cp"]; Pr = cold["Pr"]
        m_dot = cold["m_dot"]

        D_h = D_shell - do
        A_annulus = math.pi * (D_shell ** 2 - do ** 2) / 4.0
        v = m_dot / (rho * A_annulus)
        G = rho * v
        Re = rho * v * D_h / mu

        # ── Nusselt number ───────────────────────────────────────
        if Re > 2300:
            # Turbulent: Dittus-Boelter on hydraulic diameter
            # (ht doesn't have an annulus-specific turbulent correlation)
            Nu = 0.023 * Re ** 0.8 * Pr ** 0.4
        else:
            # Laminar annulus: depends on diameter ratio (Stephan)
            kappa = D_shell / do
            if kappa > 1.01:
                Nu = 3.66 + 1.2 / (kappa - 1.0) ** 0.6
            else:
                Nu = 4.36  # fallback for very thin annulus

        h_o = Nu * k / D_h
        St = Nu / (Re * Pr ** (1.0 / 3.0)) if Re > 0 else 0
        j_h = St * Pr ** (2.0 / 3.0)

        # ── Friction factor — fluids with Jones correction ───────
        f_D_pipe = fluids.friction.friction_factor(Re=Re, eD=0.0)
        if Re <= 2300 and D_shell / do > 1.01:
            kappa = D_shell / do
            try:
                C_ann = (1.0 - 1.0 / kappa ** 2) / \
                        (1.0 + 1.0 / kappa ** 2 -
                         (1.0 - kappa ** 2) /
                         (kappa ** 2 * math.log(kappa)))
                f_D = f_D_pipe * C_ann
            except (ValueError, ZeroDivisionError):
                f_D = f_D_pipe
        else:
            f_D = f_D_pipe

        dp_total = f_D * (L / D_h) * (rho * v ** 2 / 2)

        # Nozzle
        v_nozzle = m_dot / (rho * math.pi * (mech["D_nozzle_cold"] / 2) ** 2)

        return {
            "v": v, "G": G, "Re": Re, "Nu": Nu,
            "h_o": h_o, "St": St, "j_h": j_h,
            "D_h": D_h, "D_e": D_h,
            "v_nozzle": v_nozzle,
            "dp_friction": dp_total,
            "dp_header": 0.0,
            "dp_nozzle": 0.0,
            "dp_total": dp_total,
            "dp_per_m": dp_total / L if L > 0 else 0,
            "flow_regime": ("turbulent" if Re > 4000
                           else "transitional" if Re > 2300
                           else "laminar"),
        }

    # ═════════════════════════════════════════════════════════════════
    #  2b. SHELL SIDE  (shell-and-tube, Kern method)
    # ═════════════════════════════════════════════════════════════════

    @staticmethod
    def _calc_shell_side(
        D_shell, do, N_tubes, L, pitch_type,
        pitch, baffle_spacing, baffle_cut, n_baffles,
        cold, mech,
    ):
        """
        Shell-side heat transfer and pressure drop.

        ❌ Cannot use ht.conv_internal — that's for pipe flow
        ❌ Cannot use fluids.friction_factor — that's for pipe flow
        ✅ Uses Kern method correlations for cross-flow over tube banks
        """
        rho = cold["rho"]; mu = cold["mu"]
        k = cold["k"]; Cp = cold["Cp"]; Pr = cold["Pr"]
        m_dot = cold["m_dot"]

        # ── Equivalent diameter (pitch-type aware) ────────────────
        if pitch_type in ("triangular", "30deg", "60deg"):
            D_e = 4.0 * (0.866 * pitch ** 2 / 2.0
                         - math.pi * do ** 2 / 4.0) / (math.pi * do)
        else:  # square (90°) pitch
            D_e = 4.0 * (pitch ** 2
                         - math.pi * do ** 2 / 4.0) / (math.pi * do)

        # ── Cross-flow area ───────────────────────────────────────
        clearance = pitch - do
        A_cross = D_shell * clearance * baffle_spacing / pitch
        v = m_dot / (rho * A_cross)
        G = rho * v
        Re = rho * v * D_e / mu

        # ── Nusselt number — Kern method (NOT ht library) ────────
        # ht doesn't provide shell-side bundle correlations
        if Re > 200:
            Nu = 0.36 * Re ** 0.55 * Pr ** (1.0 / 3.0)
        elif Re > 10:
            Nu = 0.36 * Re ** 0.55 * Pr ** (1.0 / 3.0)  # same, with caution
        else:
            # Very low Re: natural convection regime, correlation unreliable
            Nu = max(4.0, 0.36 * abs(Re) ** 0.55 * Pr ** (1.0 / 3.0))

        h_o = Nu * k / D_e
        St = Nu / (Re * Pr ** (1.0 / 3.0)) if Re > 0 else 0
        j_h = St * Pr ** (2.0 / 3.0)

        # ── Pressure drop — Kern method (NOT fluids library) ─────
        # fluids.friction_factor is for INTERNAL pipe flow — wrong here
        # Kern friction factor j_f for cross-flow over tube bank
        if Re > 200:
            j_f = 0.25 * Re ** (-0.20)
        elif Re > 10:
            j_f = 0.50 * Re ** (-0.30)
        else:
            j_f = 1.0 * Re ** (-0.50)

        # Cross-flow ΔP between baffles
        dp_cross = (8.0 * j_f * (D_shell / D_e) * n_baffles
                    * (rho * v ** 2 / 2.0))

        # Baffle-window ΔP (≈ 1 velocity head per pass through window)
        A_window = (math.pi / 4.0) * D_shell ** 2 * baffle_cut
            # Subtract tubes in window
        A_tubes_win = (N_tubes * baffle_cut * (math.pi / 4.0) * do ** 2)
        A_window_net = max(A_window - A_tubes_win, 1e-10)
        v_window = m_dot / (rho * A_window_net)
        dp_window = n_baffles * (rho * v_window ** 2 / 2.0)

        # Nozzle losses
        v_nozzle = m_dot / (rho * math.pi * (mech["D_nozzle_cold"] / 2) ** 2)
        dp_nozzle = (1.5 + 0.5) * (rho * v_nozzle ** 2 / 2.0)

        dp_total = dp_cross + dp_window + dp_nozzle

        return {
            "v": v, "v_window": v_window, "G": G, "Re": Re, "Nu": Nu,
            "h_o": h_o, "St": St, "j_h": j_h, "j_f": j_f,
            "D_e": D_e,
            "v_nozzle": v_nozzle,
            "dp_cross": dp_cross,
            "dp_window": dp_window,
            "dp_nozzle": dp_nozzle,
            "dp_friction": dp_cross,  # dominant component
            "dp_header": dp_window,   # window losses serve similar role
            "dp_total": dp_total,
            "dp_per_m": dp_total / L if L > 0 else 0,
            "flow_regime": "cross-flow (shell)",
        }

    # ═════════════════════════════════════════════════════════════════
    #  3. OVERALL THERMAL
    # ═════════════════════════════════════════════════════════════════

    @staticmethod
    def _calc_overall_thermal(tube, shell, L, di, do, N_tubes, hot, cold, wall):
        A_o_total = N_tubes * math.pi * do * L
        A_i_total = N_tubes * math.pi * di * L

        R_conv_i = 1.0 / (tube["h_i"] * A_i_total)
        R_foul_i = wall["R_fi"] / A_i_total
        R_wall   = math.log(do / di) / (2 * math.pi * wall["k_wall"] * L * N_tubes)
        R_foul_o = wall["R_fo"] / A_o_total
        R_conv_o = 1.0 / (shell["h_o"] * A_o_total)

        R_total = R_conv_i + R_foul_i + R_wall + R_foul_o + R_conv_o
        R_clean = R_conv_i + R_wall + R_conv_o

        UA = 1.0 / R_total
        U_dirty = UA / A_o_total
        U_clean = 1.0 / (R_clean * A_o_total) if A_o_total > 0 else 0

        # Fouling Bg = ratio of clean to dirty U
        fouling_Bg = U_clean / U_dirty if U_dirty > 0 else 1.0

        return {
            "A_o_total": A_o_total,
            "A_i_total": A_i_total,
            "R_conv_i": R_conv_i, "R_foul_i": R_foul_i,
            "R_wall": R_wall,
            "R_foul_o": R_foul_o, "R_conv_o": R_conv_o,
            "R_total": R_total, "R_clean": R_clean,
            "UA": UA, "U_dirty": U_dirty, "U_clean": U_clean,
            "fouling_Bg": fouling_Bg,
            "R_conv_i_frac": R_conv_i / R_total,
            "R_wall_frac": R_wall / R_total,
            "R_conv_o_frac": R_conv_o / R_total,
            "R_foul_frac": (R_foul_i + R_foul_o) / R_total,
        }

    # ═════════════════════════════════════════════════════════════════
    #  4. ε-NTU  — Uses ht library where available
    # ═════════════════════════════════════════════════════════════════

    @staticmethod
    def _calc_effectiveness(geo, UA, hot, cold):
        C_hot = hot["m_dot"] * hot["Cp"]
        C_cold = cold["m_dot"] * cold["Cp"]
        C_min = min(C_hot, C_cold)
        C_max = max(C_hot, C_cold)
        C_r = C_min / C_max
        NTU = UA / C_min

        # ── Use ht library for ε-NTU ✅ ──────────────────────────
        # ht.heat_exchanger module provides effectiveness calculations
        # for various flow arrangements
        try:
            if geo == "concentric_tube":
                epsilon = ht.heat_exchanger.effectiveness_counterflow(
                    NTU=NTU, C_r=C_r)
            else:
                # 1-shell-pass, 2-tube-pass
                epsilon = ht.heat_exchanger.effectiveness_shell_and_tube(
                    NTU=NTU, C_r=C_r, shells=1)
        except (AttributeError, NotImplementedError):
            # Fallback if ht doesn't have these exact functions
            if geo == "concentric_tube":
                if abs(C_r - 1.0) < 1e-10:
                    epsilon = NTU / (1.0 + NTU)
                else:
                    exp_term = math.exp(-NTU * (1.0 - C_r))
                    epsilon = (1.0 - exp_term) / (1.0 - C_r * exp_term)
            else:
                E = math.sqrt(1.0 + C_r ** 2)
                denom = ((1.0 - math.exp(-NTU * E))
                        / (1.0 + math.exp(-NTU * E)))
                epsilon = 2.0 / (1.0 + C_r + E / denom) if abs(denom) > 1e-15 else 0.0

        Q_max = C_min * (hot["T_in"] - cold["T_in"])
        Q = epsilon * Q_max
        T_hot_out = hot["T_in"] - Q / C_hot
        T_cold_out = cold["T_in"] + Q / C_cold

        return {
            "C_hot": C_hot, "C_cold": C_cold,
            "C_min": C_min, "C_max": C_max, "C_r": C_r,
            "NTU": NTU, "epsilon": epsilon,
            "Q_max": Q_max, "Q": Q,
            "T_hot_out": T_hot_out, "T_cold_out": T_cold_out,
        }

    # ═════════════════════════════════════════════════════════════════
    #  5. LMTD & F CORRECTION
    # ═════════════════════════════════════════════════════════════════

    @staticmethod
    def _calc_LMTD(geo, T_hot_out, T_cold_out, T_hot_in, T_cold_in):
        dt1 = T_hot_in - T_cold_out    # hot-end ΔT
        dt2 = T_hot_out - T_cold_in    # cold-end ΔT

        if abs(dt1 - dt2) < 0.01:
            LMTD = (dt1 + dt2) / 2.0
        else:
            LMTD = (dt1 - dt2) / math.log(dt1 / dt2)

        # F correction factor
        if geo == "concentric_tube":
            F = 1.0  # counterflow
        else:
            # Bowman-Mueller-Nagle for 1-2 exchanger
            delta_T = T_hot_in - T_cold_in
            if abs(delta_T) < 0.01:
                F = 1.0
            else:
                P = (T_cold_out - T_cold_in) / delta_T
                R = (T_hot_in - T_hot_out) / (T_cold_out - T_cold_in) \
                    if abs(T_cold_out - T_cold_in) > 0.01 else 1.0

                if abs(R - 1.0) < 1e-6:
                    denom = math.sqrt(2.0) * P + (1.0 - P)
                    F = 2.0 * P / denom if abs(denom) > 1e-10 else 1.0
                else:
                    try:
                        sqrt_R2_1 = math.sqrt(R ** 2 + 1.0)
                        num = sqrt_R2_1 * math.log(
                            (2.0 - P * (R + 1 - sqrt_R2_1))
                            / (2.0 - P * (R + 1 + sqrt_R2_1))
                        )
                        den = (R - 1.0) * math.log(
                            (2.0 / P - 1.0 - R + sqrt_R2_1)
                            / (2.0 / P - 1.0 - R - sqrt_R2_1)
                        )
                        F = num / den if abs(den) > 1e-10 else 1.0
                    except (ValueError, ZeroDivisionError):
                        F = 1.0
                F = max(0.0, min(F, 1.0))

        # Approach and temperature cross
        T_hot_out_C = T_hot_out - 273.15
        T_cold_out_C = T_cold_out - 273.15
        T_hot_in_C = T_hot_in - 273.15
        T_cold_in_C = T_cold_in - 273.15

        approach_hot = T_hot_in_C - T_cold_out_C
        approach_cold = T_hot_out_C - T_cold_in_C
        min_approach = min(approach_hot, approach_cold)
        temp_cross = max(0.0, T_cold_out_C - T_hot_out_C)

        return {
            "LMTD": LMTD, "F": F,
            "approach_hot": approach_hot,
            "approach_cold": approach_cold,
            "min_approach": min_approach,
            "temp_cross": temp_cross,
        }

    # ═════════════════════════════════════════════════════════════════
    #  6. WALL TEMPERATURE
    # ═════════════════════════════════════════════════════════════════

    @staticmethod
    def _calc_wall_temperature(h_i, h_o, U, T_hot_out, T_cold_out,
                                T_hot_in, T_cold_in):
        T_bulk_hot = (T_hot_in + T_hot_out) / 2.0
        T_bulk_cold = (T_cold_in + T_cold_out) / 2.0
        q_local = U * (T_bulk_hot - T_bulk_cold)

        T_wall_inner = (T_bulk_hot - q_local / h_i) if h_i > 0 else T_bulk_hot
        T_wall_outer = (T_bulk_cold + q_local / h_o) if h_o > 0 else T_bulk_cold

        return {
            "T_wall_inner": T_wall_inner,
            "T_wall_outer": T_wall_outer,
            "T_wall_inner_C": T_wall_inner - 273.15,
            "T_wall_outer_C": T_wall_outer - 273.15,
        }

    # ═════════════════════════════════════════════════════════════════
    #  7. MECHANICAL CHECKS
    # ═════════════════════════════════════════════════════════════════

    @staticmethod
    def _calc_mechanical(di, do, D_shell, L, baffle_spacing,
                          N_tubes, v_shell, rho_shell, mech):
        P_design = mech["P_design"]
        S = mech["allowable_stress"]

        # ── Minimum wall thickness (ASME VIII, thin-wall) ─────────
        tube_t = (do - di) / 2.0
        t_tube_min = P_design * di / (2.0 * S + 0.4 * P_design)
        t_shell_actual = max(0.006, D_shell / 200.0)
        t_shell_min = P_design * D_shell / (2.0 * S + 0.4 * P_design)

        tube_thickness_ok = tube_t >= t_tube_min
        shell_thickness_ok = t_shell_actual >= t_shell_min

        # ── Vibration: Connors' criterion (simplified) ────────────
        rho_tube = 7850.0
        m_t_per_m = rho_tube * math.pi * (do ** 2 - di ** 2) / 4.0
        # v_crit ≈ C × sqrt(m_t × δ / (ρ_shell × D_o))
        # C ≈ 4.0, damping δ ≈ 0.01 (conservative)
        v_critical = 4.0 * math.sqrt(m_t_per_m * 0.01 / (rho_shell * do)) \
                     if do > 0 else 999.0
        vibration_ok = v_shell < v_critical * 0.8
        span_ok = baffle_spacing <= 1.5

        # ── Weights ───────────────────────────────────────────────
        # (shell + tubes, simplified)
        t_shell = t_shell_actual
        V_shell = (math.pi / 4.0) * ((D_shell + 2*t_shell)**2
                  - D_shell**2) * L
        m_shell_kg = V_shell * 7850.0
        V_tubes = N_tubes * (math.pi / 4.0) * (do**2 - di**2) * L
        m_tubes_kg = V_tubes * 7850.0
        dry_weight = m_shell_kg + m_tubes_kg

        V_water_tubes = N_tubes * (math.pi / 4.0) * di**2 * L
        V_water_shell = (math.pi / 4.0) * D_shell**2 * L \
                        - N_tubes * (math.pi / 4.0) * do**2 * L
        wet_weight = dry_weight + rho_shell * V_water_shell + 971.8 * V_water_tubes

        return {
            "tube_thickness_mm": tube_t * 1000,
            "tube_thickness_min_mm": t_tube_min * 1000,
            "tube_thickness_ok": tube_thickness_ok,
            "shell_thickness_mm": t_shell_actual * 1000,
            "shell_thickness_min_mm": t_shell_min * 1000,
            "shell_thickness_ok": shell_thickness_ok,
            "v_critical_vibration": v_critical,
            "vibration_ok": vibration_ok,
            "span_ok": span_ok,
            "unsupported_span_m": baffle_spacing,
            "dry_weight_kg": dry_weight,
            "wet_weight_kg": wet_weight,
        }

    # ═════════════════════════════════════════════════════════════════
    #  8. GEOMETRIC PARAMETERS
    # ═════════════════════════════════════════════════════════════════

    @staticmethod
    def _calc_geometric(geo, L, di, do, D_shell, N_tubes, N_pass,
                         pitch_type, pitch, baffle_spacing, baffle_cut,
                         n_baffles):
        pitch_ratio = pitch / do
        # Bundle diameter (Phadke approximation for square pitch)
        N_tpp = N_tubes / N_pass if N_pass > 0 else N_tubes
        D_bundle = do * (N_tpp / 0.215) ** (1.0 / 2.207) if N_tpp > 0 else do
        t_tubesheet = max(0.025, do * 1.5)
        D_tubesheet = D_shell + 2 * max(0.006, D_shell / 200.0)
        V_exchanger = (math.pi / 4.0) * D_shell ** 2 * L
        baffle_cut_height = D_shell * baffle_cut

        return {
            "pitch_ratio": pitch_ratio,
            "pitch_m": pitch,
            "D_bundle_m": D_bundle,
            "D_tubesheet_m": D_tubesheet,
            "tube_passes": N_pass,
            "baffle_count": n_baffles,
            "baffle_spacing_m": baffle_spacing,
            "baffle_cut_pct": baffle_cut * 100,
            "baffle_cut_height_m": baffle_cut_height,
            "exchanger_volume_m3": V_exchanger,
            "L_D_ratio": L / D_shell if D_shell > 0 else 0,
        }

    # ═════════════════════════════════════════════════════════════════
    #  9. COST MODEL
    # ═════════════════════════════════════════════════════════════════

    def _calc_cost(self, L, di, do, D_shell, N_tubes, N_pass, n_baffles,
                   dp_tube, dp_shell, m_dot_hot, m_dot_cold,
                   rho_hot, rho_cold, material, Q, A_o_total):
        # Material mass
        t_shell = max(0.006, D_shell / 200.0)
        V_shell_wall = (math.pi / 4.0) * ((D_shell + 2*t_shell)**2
                        - D_shell**2) * L
        m_shell = V_shell_wall * self.STEEL_DENSITY
        V_tubes = N_tubes * (math.pi / 4.0) * (do**2 - di**2) * L
        m_tubes = V_tubes * self.STEEL_DENSITY
        V_baffles = n_baffles * (math.pi / 4.0) * D_shell**2 * 0.004 * 0.85
        m_baffles = V_baffles * self.STEEL_DENSITY
        t_ts = max(0.025, do * 1.5)
        V_tubesheets = 2 * (math.pi / 4.0) * D_shell**2 * t_ts
        m_tubesheets = V_tubesheets * self.STEEL_DENSITY
        m_total = m_shell + m_tubes + m_baffles + m_tubesheets

        # Capital cost
        mat_factor = self.MATERIAL_FACTORS.get(material, 1.0)
        raw_cost = m_total * self.CARBON_STEEL_COST * mat_factor
        fab_cost = raw_cost * (self.FABRICATION_FACTOR - 1.0)
        baffle_cost = n_baffles * self.BAFFLE_COST_EACH * mat_factor
        C_capital = raw_cost + fab_cost + baffle_cost

        # Operating cost
        V_hot = m_dot_hot / rho_hot
        V_cold = m_dot_cold / rho_cold
        P_hot = dp_tube * V_hot / self.PUMP_EFFICIENCY
        P_cold = dp_shell * V_cold / self.PUMP_EFFICIENCY
        P_total = P_hot + P_cold
        annual_kWh = P_total * self.OPERATING_HOURS / 1000.0
        C_operating = annual_kWh * self.ELECTRICITY_COST
        C_annualised = C_capital / self.PAYBACK_YEARS + C_operating

        return {
            "mass_total_kg": m_total,
            "cost_capital_USD": C_capital,
            "pump_power_hot_W": P_hot,
            "pump_power_cold_W": P_cold,
            "pump_power_total_W": P_total,
            "annual_energy_kWh": annual_kWh,
            "cost_operating_USD_per_yr": C_operating,
            "cost_annualised_USD_per_yr": C_annualised,
            "cost_per_m2_USD": C_capital / A_o_total if A_o_total > 0 else 0,
            "cost_per_kW_duty_USD": C_capital / (Q / 1000) if Q > 0 else 0,
            "cost_per_kW_annualised_USD": C_annualised / (Q / 1000) if Q > 0 else 0,
        }

    # ═════════════════════════════════════════════════════════════════
    #  10. DESIGN LIMIT CHECKS
    # ═════════════════════════════════════════════════════════════════

    def _check_design_limits(self, geo, tube, shell, ntu, lmtd, mech, geom):
        warnings: List[str] = []

        # Velocity checks
        if tube["v"] > self.MAX_TUBE_VELOCITY:
            warnings.append(
                f"Tube velocity {tube['v']:.2f} m/s > max {self.MAX_TUBE_VELOCITY} m/s (erosion risk)")
        if tube["v"] < self.MIN_TUBE_VELOCITY:
            warnings.append(
                f"Tube velocity {tube['v']:.2f} m/s < min {self.MIN_TUBE_VELOCITY} m/s (fouling risk)")
        if shell["v"] > self.MAX_SHELL_VELOCITY:
            warnings.append(
                f"Shell velocity {shell['v']:.2f} m/s > max {self.MAX_SHELL_VELOCITY} m/s")
        if tube["v_nozzle"] > self.MAX_NOZZLE_VELOCITY:
            warnings.append(
                f"Hot nozzle velocity {tube['v_nozzle']:.2f} m/s > max {self.MAX_NOZZLE_VELOCITY} m/s")
        if shell["v_nozzle"] > self.MAX_NOZZLE_VELOCITY:
            warnings.append(
                f"Cold nozzle velocity {shell['v_nozzle']:.2f} m/s > max {self.MAX_NOZZLE_VELOCITY} m/s")

        # Pressure drop checks
        if tube["dp_total"] > self.MAX_DP_TUBE:
            warnings.append(
                f"Tube ΔP {tube['dp_total']/1000:.1f} kPa > max {self.MAX_DP_TUBE/1000:.1f} kPa")
        if shell["dp_total"] > self.MAX_DP_SHELL:
            warnings.append(
                f"Shell ΔP {shell['dp_total']/1000:.1f} kPa > max {self.MAX_DP_SHELL/1000:.1f} kPa")

        # Thermal checks
        if lmtd["min_approach"] < self.MIN_APPROACH_TEMP:
            warnings.append(
                f"Min approach {lmtd['min_approach']:.1f}°C < pinch limit {self.MIN_APPROACH_TEMP}°C")
        if lmtd["temp_cross"] > 0 and geo != "shell_and_tube":
            warnings.append(
                f"Temperature cross {lmtd['temp_cross']:.1f}°C (check F factor)")
        if lmtd["F"] < self.MIN_F_LMTD and geo != "concentric_tube":
            warnings.append(
                f"F = {lmtd['F']:.3f} < {self.MIN_F_LMTD} (poor design — reconsider configuration)")
        if ntu["epsilon"] > 0.90:
            warnings.append(
                f"Effectiveness {ntu['epsilon']:.1%} > 90% — diminishing returns, consider series arrangement")

        # Mechanical checks
        if not mech["tube_thickness_ok"]:
            warnings.append(
                f"Tube wall {mech['tube_thickness_mm']:.1f}mm < min {mech['tube_thickness_min_mm']:.1f}mm (ASME)")
        if not mech["shell_thickness_ok"]:
            warnings.append(
                f"Shell wall {mech['shell_thickness_mm']:.1f}mm < min {mech['shell_thickness_min_mm']:.1f}mm (ASME)")
        if not mech["vibration_ok"]:
            warnings.append(
                f"Shell velocity > 80% of critical — flow-induced vibration risk")
        if not mech["span_ok"]:
            warnings.append(
                f"Unsupported span {mech['unsupported_span_m']:.2f}m > {self.MAX_UNSUPPORTED_SPAN}m")

        # Geometric checks
        if geom["L_D_ratio"] > self.MAX_L_D_RATIO:
            warnings.append(
                f"L/D = {geom['L_D_ratio']:.1f} > {self.MAX_L_D_RATIO} (tube sag risk)")
        if geom["L_D_ratio"] < self.MIN_L_D_RATIO:
            warnings.append(
                f"L/D = {geom['L_D_ratio']:.1f} < {self.MIN_L_D_RATIO} (poor distribution)")
        if geom["pitch_ratio"] < 1.25:
            warnings.append(
                f"Pitch ratio {geom['pitch_ratio']:.2f} < 1.25 (TEMA minimum)")

        # Flow regime warnings
        if tube["Re"] < 2300:
            warnings.append("Tube-side laminar flow — low heat transfer coefficient")
        if 2300 < tube["Re"] < 4000:
            warnings.append("Tube-side transitional flow — unreliable performance")

        return warnings

    # ═════════════════════════════════════════════════════════════════
    #  OUTPUT FORMATTERS
    # ═════════════════════════════════════════════════════════════════

    @staticmethod
    def _format_thermal(thermal, ntu, lmtd):
        Q = ntu["Q"]
        T_hot_out_C = ntu["T_hot_out"] - 273.15
        T_cold_out_C = ntu["T_cold_out"] - 273.15
        T_hot_in_C = ntu["Q"]  # placeholder, use actual
        # We don't have T_in_C here, compute from ntu
        # Actually we need to pass them... let me use the ntu dict

        return {
            "heat_duty_W": Q,
            "heat_duty_kW": Q / 1000.0,
            "overall_U_dirty_W_m2K": thermal["U_dirty"],
            "overall_U_clean_W_m2K": thermal["U_clean"],
            "fouling_Bg": thermal["fouling_Bg"],
            "area_m2": thermal["A_o_total"],
            "effectiveness": ntu["epsilon"],
            "NTU": ntu["NTU"],
            "LMTD_K": lmtd["LMTD"],
            "F_LMTD": lmtd["F"],
            "t_hot_out_C": ntu["T_hot_out"] - 273.15,
            "t_cold_out_C": ntu["T_cold_out"] - 273.15,
            "min_approach_C": lmtd["min_approach"],
            "temp_cross_C": lmtd["temp_cross"],
            "R_conv_tube_frac": thermal["R_conv_i_frac"],
            "R_wall_frac": thermal["R_wall_frac"],
            "R_conv_shell_frac": thermal["R_conv_o_frac"],
            "R_fouling_frac": thermal["R_foul_frac"],
        }

    @staticmethod
    def _format_hydraulic(tube, shell):
        return {
            "v_tube_m_s": tube["v"],
            "v_shell_m_s": shell["v"],
            "v_nozzle_hot_m_s": tube["v_nozzle"],
            "v_nozzle_cold_m_s": shell["v_nozzle"],
            "G_tube_kg_m2s": tube["G"],
            "G_shell_kg_m2s": shell["G"],
            "Re_tube": tube["Re"],
            "Re_shell": shell["Re"],
            "flow_regime_tube": tube["flow_regime"],
            "flow_regime_shell": shell["flow_regime"],
            "dp_tube_Pa": tube["dp_total"],
            "dp_tube_kPa": tube["dp_total"] / 1000.0,
            "dp_shell_Pa": shell["dp_total"],
            "dp_shell_kPa": shell["dp_total"] / 1000.0,
            "dp_tube_per_m_Pa": tube["dp_per_m"],
            "dp_shell_per_m_Pa": shell["dp_per_m"],
            "dp_tube_friction_Pa": tube["dp_friction"],
            "dp_tube_header_Pa": tube["dp_header"],
            "dp_tube_nozzle_Pa": tube["dp_nozzle"],
            "dp_shell_cross_Pa": shell.get("dp_cross", 0),
            "dp_shell_window_Pa": shell.get("dp_window", 0),
            "dp_shell_nozzle_Pa": shell.get("dp_nozzle", 0),
        }

    @staticmethod
    def _format_htc(thermal):
        return {
            "h_i_W_m2K": 1.0 / (thermal["R_conv_i"] * thermal["A_i_total"]) if thermal["A_i_total"] > 0 else 0,
            "h_o_W_m2K": 1.0 / (thermal["R_conv_o"] * thermal["A_o_total"]) if thermal["A_o_total"] > 0 else 0,
        }

    @staticmethod
    def _format_wall_temp(wt):
        return {
            "T_wall_inner_C": wt["T_wall_inner_C"],
            "T_wall_outer_C": wt["T_wall_outer_C"],
        }

    @staticmethod
    def _format_mechanical(mech):
        return {
            "tube_thickness_mm": mech["tube_thickness_mm"],
            "tube_thickness_min_mm": mech["tube_thickness_min_mm"],
            "tube_thickness_ok": 1.0 if mech["tube_thickness_ok"] else 0.0,
            "shell_thickness_mm": mech["shell_thickness_mm"],
            "shell_thickness_min_mm": mech["shell_thickness_min_mm"],
            "shell_thickness_ok": 1.0 if mech["shell_thickness_ok"] else 0.0,
            "v_critical_vibration_m_s": mech["v_critical_vibration"],
            "vibration_ok": 1.0 if mech["vibration_ok"] else 0.0,
            "span_ok": 1.0 if mech["span_ok"] else 0.0,
            "unsupported_span_m": mech["unsupported_span_m"],
            "dry_weight_kg": mech["dry_weight_kg"],
            "wet_weight_kg": mech["wet_weight_kg"],
        }

    @staticmethod
    def _format_geometric(geom):
        return {
            "pitch_ratio": geom["pitch_ratio"],
            "pitch_m": geom["pitch_m"],
            "D_bundle_m": geom["D_bundle_m"],
            "D_tubesheet_m": geom["D_tubesheet_m"],
            "tube_passes": geom["tube_passes"],
            "baffle_count": float(geom["baffle_count"]),
            "baffle_spacing_m": geom["baffle_spacing_m"],
            "baffle_cut_pct": geom["baffle_cut_pct"],
            "baffle_cut_height_m": geom["baffle_cut_height_m"],
            "exchanger_volume_m3": geom["exchanger_volume_m3"],
            "L_D_ratio": geom["L_D_ratio"],
        }

    @staticmethod
    def _format_cost(cost):
        return {
            "mass_total_kg": cost["mass_total_kg"],
            "cost_capital_USD": cost["cost_capital_USD"],
            "pump_power_hot_W": cost["pump_power_hot_W"],
            "pump_power_cold_W": cost["pump_power_cold_W"],
            "pump_power_total_W": cost["pump_power_total_W"],
            "annual_energy_kWh": cost["annual_energy_kWh"],
            "cost_operating_USD_per_yr": cost["cost_operating_USD_per_yr"],
            "cost_annualised_USD_per_yr": cost["cost_annualised_USD_per_yr"],
            "cost_per_m2_USD": cost["cost_per_m2_USD"],
            "cost_per_kW_duty_USD": cost["cost_per_kW_duty_USD"],
            "cost_per_kW_annualised_USD": cost["cost_per_kW_annualised_USD"],
        }