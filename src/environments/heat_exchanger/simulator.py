from typing import Dict, Any, Tuple
import math
import ht
import fluids
from ...core.base_simulator import BaseSimulator

class HeatExchangerSimulator(BaseSimulator):
    def simulate(self, design_params: Dict[str, Any]) -> Tuple[bool, Dict[str, float], Dict[str, Any], str]:
        try:
            geo_type = design_params["geometry_type"]
            L = design_params["length"]
            di = design_params["inner_tube_di"]
            do = design_params["inner_tube_do"]
            D_shell = design_params["outer_shell_di"]
            N_tubes = design_params["number_of_tubes"]
            
            m_dot_hot = 1.0  # kg/s
            T_hot_in = 80 + 273.15  # K
            rho_hot = 971.8  # kg/m^3 (80C water)
            mu_hot = 3.55e-4 # Pa.s
            k_hot = 0.67     # W/m.K
            Cp_hot = 4190    # J/kg.K
            Pr_hot = 2.2
            
            m_dot_cold = 1.0 # kg/s
            T_cold_in = 20 + 273.15 # K
            rho_cold = 998.2
            mu_cold = 10.02e-4
            k_cold = 0.598
            Cp_cold = 4182
            Pr_cold = 7.0
            
            k_wall = 50.0 # W/m.K
            
            # 1. Hot fluid inside tubes
            A_tube_in_total = N_tubes * math.pi * (di / 2)**2
            v_hot = m_dot_hot / (rho_hot * A_tube_in_total)
            Re_hot = rho_hot * v_hot * di / mu_hot
            
            if Re_hot > 2300:
                Nu_hot = ht.conv_internal.Nu_conv_internal(Re=Re_hot, Pr=Pr_hot, eD=0)
            else:
                Nu_hot = 4.36
            h_i = Nu_hot * k_hot / di
            
            fd_hot = fluids.friction.friction_factor(Re=Re_hot, eD=0)
            dp_hot = fd_hot * (L / di) * (rho_hot * v_hot**2 / 2)
            
            # 2. Cold fluid inside shell/annulus
            if geo_type == "concentric_tube":
                D_h = D_shell - do
                A_annulus = math.pi * (D_shell**2 - do**2) / 4
                v_cold = m_dot_cold / (rho_cold * A_annulus)
                Re_cold = rho_cold * v_cold * D_h / mu_cold
                
                if Re_cold > 2300:
                    Nu_cold = ht.conv_internal.Nu_conv_internal(Re=Re_cold, Pr=Pr_cold, eD=0)
                else:
                    Nu_cold = 4.36
                h_o = Nu_cold * k_cold / D_h
                
                fd_cold = fluids.friction.friction_factor(Re=Re_cold, eD=0)
                dp_cold = fd_cold * (L / D_h) * (rho_cold * v_cold**2 / 2)
                
            else: # shell_and_tube
                baffle_spacing = design_params.get("baffle_spacing", L/5)
                if baffle_spacing == 0:
                    baffle_spacing = L / 5
                pitch = do * 1.25
                clearance = pitch - do
                A_shell_cross = D_shell * clearance * baffle_spacing / pitch
                v_cold = m_dot_cold / (rho_cold * A_shell_cross)
                D_e = 4 * (pitch**2 - (math.pi * do**2 / 4)) / (math.pi * do)
                Re_cold = rho_cold * v_cold * D_e / mu_cold
                
                Nu_cold = 0.36 * (Re_cold**0.55) * (Pr_cold**(1/3))
                h_o = Nu_cold * k_cold / D_e
                
                dp_cold = 2 * fluids.friction.friction_factor(Re=Re_cold, eD=0) * (D_shell / D_e) * (L / baffle_spacing) * (rho_cold * v_cold**2 / 2)

            # 3. Overall Heat Transfer Coefficient (U)
            A_o_total = N_tubes * math.pi * do * L
            A_i_total = N_tubes * math.pi * di * L
            
            R_i = 1 / (h_i * A_i_total)
            R_wall = math.log(do / di) / (2 * math.pi * k_wall * L * N_tubes)
            R_o = 1 / (h_o * A_o_total)
            R_total = R_i + R_wall + R_o
            
            UA = 1 / R_total
            
            # 4. NTU Method for Effectiveness and Heat Duty
            C_hot = m_dot_hot * Cp_hot
            C_cold = m_dot_cold * Cp_cold
            C_min = min(C_hot, C_cold)
            C_max = max(C_hot, C_cold)
            C_r = C_min / C_max
            NTU = UA / C_min
            
            if C_r == 1:
                epsilon = NTU / (1 + NTU)
            else:
                epsilon = (1 - math.exp(-NTU * (1 - C_r))) / (1 - C_r * math.exp(-NTU * (1 - C_r)))
                
            Q_max = C_min * (T_hot_in - T_cold_in)
            Q = epsilon * Q_max
            
            T_hot_out = T_hot_in - Q / C_hot
            T_cold_out = T_cold_in + Q / C_cold
            
            metrics = {
                "heat_duty": Q,
                "pressure_drop_tube": dp_hot,
                "pressure_drop_shell": dp_cold,
                "total_pressure_drop": dp_hot + dp_cold,
                "overall_U": UA / A_o_total,
                "area": A_o_total,
                "t_hot_out": T_hot_out - 273.15,
                "t_cold_out": T_cold_out - 273.15
            }
            
            raw_data = {
                "Re_hot": Re_hot,
                "Re_cold": Re_cold,
                "h_i": h_i,
                "h_o": h_o,
                "epsilon": epsilon
            }
            
            for k, v in metrics.items():
                if math.isnan(v) or math.isinf(v):
                    return False, {}, {}, f"Calculated metric ({k}) is invalid (NaN/Inf)."
            
            return True, metrics, raw_data, ""
            
        except Exception as e:
            return False, {}, {}, f"Unexpected error during simulation: {str(e)}"
