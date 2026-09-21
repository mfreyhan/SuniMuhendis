# Throughflow capability observations

These are observed executions, not certified support or physical validation.

All scenarios use NASA commit `23c2b0bf781b4b030014f458ecfde872896777a2`.

Explicit `fixed_streamlines` cases disable upstream streamline adjustment; they do not reduce the requested streamline count.

Row massflow spread is `(max - min) / abs(mean)` over `total_massflow_no_coolant`. It is a diagnostic, not a full energy/radial-equilibrium acceptance test.

## py312_followup

{"counts": {"error": 5, "completed": 1}, "cases": 6, "median_process_elapsed_seconds": 1.9071621500006586, "maximum_process_elapsed_seconds": 6.57824840000103, "max_peak_working_set_bytes": 217669632}

| Case | Observed status | Result / diagnostic |
|---|---|---|
| followup_compressor10_openpyxl | error | blade row 1 (IGV, stage 1) cannot pass the requested massflow. Required flow function m~ = 0.7238 exceeds the choked limit m~_max = 0.5786 for gamma = 1.401 - no Mach number can satisfy this.   target massflow : 54.4000 kg/s   P0  |
| followup_compressor_aungier_0.3 | error |  ******************************************************************************* CanteraError thrown by Phase::setDensity: density must be positive. density = -0.062499080467742496 ************************************************* |
| followup_compressor_aungier_0.5 | error | rotor relative Mach converged onto the upper edge of its search bracket [0.01, 1] at 0.999994: the solution lies outside the bracket and this result is not converged. |
| followup_compressor_aungier_0.7 | error | rotor relative Mach converged onto the upper edge of its search bracket [0.01, 1] at 0.999994: the solution lies outside the bracket and this result is not converged. |
| followup_turbine1_aba | completed | P=3394.089 kW; PR=3.385441; row mdot spread=0.00202%; eta_p=0.732031 |
| followup_turbine1_td2_warm | error | nan detected |

## py312_latest

{"counts": {"error": 37, "completed": 22}, "cases": 59, "median_process_elapsed_seconds": 1.9591027000060421, "maximum_process_elapsed_seconds": 14.812741699999606, "max_peak_working_set_bytes": 208572416}

| Case | Observed status | Result / diagnostic |
|---|---|---|
| compressor10_original | error | `Import openpyxl` failed.  Use pip or conda to install the openpyxl package. |
| compressor1_17_aungier | error | rotor relative Mach converged onto the upper edge of its search bracket [0.01, 1] at 0.999994: the solution lies outside the bracket and this result is not converged. |
| compressor1_17_original | completed | P=523.524 kW; PR=1.306379; row mdot spread=0.00008%; eta_p=1.006804 |
| compressor1_1_aungier | error | rotor relative Mach converged onto the upper edge of its search bracket [0.01, 1] at 0.999994: the solution lies outside the bracket and this result is not converged. |
| compressor1_1_original | completed | P=509.155 kW; PR=1.298718; row mdot spread=0.00006%; eta_p=1.000496 |
| compressor1_3_aungier | error | rotor relative Mach converged onto the upper edge of its search bracket [0.01, 1] at 0.999994: the solution lies outside the bracket and this result is not converged. |
| compressor1_3_diffusion | completed | P=527.297 kW; PR=1.322383; row mdot spread=0.00009%; eta_p=1.007867 |
| compressor1_3_original | completed | P=527.700 kW; PR=1.322718; row mdot spread=0.00004%; eta_p=1.007857 |
| compressor1_5_aungier | error | rotor relative Mach converged onto the upper edge of its search bracket [0.01, 1] at 0.999994: the solution lies outside the bracket and this result is not converged. |
| compressor1_5_original | completed | P=527.465 kW; PR=1.293930; row mdot spread=0.00009%; eta_p=1.008715 |
| compressor1_9_aungier | error | rotor relative Mach converged onto the upper edge of its search bracket [0.01, 1] at 0.999994: the solution lies outside the bracket and this result is not converged. |
| compressor1_9_original | completed | P=524.550 kW; PR=1.303165; row mdot spread=0.00004%; eta_p=1.007701 |
| compressor1_repeat | error | Invalid value of C 5.96 which causes Vm to be nan. Change reduce alpha/beta for RowType.Stator 2 |
| eee_hpt_original | completed | P=16785.985 kW; PR=4.812192; row mdot spread=0.00601%; eta_p=0.946749 |
| eee_hpt_td2 | error | nan detected |
| radial_original | completed | P=28.609 kW; PR=1.282142; row mdot spread=0.00732%; eta_p=1.011728 |
| turbine1_17_fixed_streamlines | completed | P=3396.787 kW; PR=3.389714; row mdot spread=0.00348%; eta_p=0.732657 |
| turbine1_17_original | error | adjust_streamlines() missing 1 required positional argument: 'massflow_fraction' |
| turbine1_17_td2 | error | nan detected |
| turbine1_1_fixed_streamlines | completed | P=3400.274 kW; PR=3.393036; row mdot spread=0.00445%; eta_p=0.733192 |
| turbine1_1_original | error | adjust_streamlines() missing 1 required positional argument: 'massflow_fraction' |
| turbine1_1_td2 | error | nan detected |
| turbine1_3_ainley_mathieson | error | The truth value of an array with more than one element is ambiguous. Use a.any() or a.all() |
| turbine1_3_craig_cox | error |  ******************************************************************************* CanteraError thrown by Phase::setTemperature: temperature must be positive. T = -nan **************************************************************** |
| turbine1_3_fixed_streamlines | completed | P=3394.089 kW; PR=3.385441; row mdot spread=0.00202%; eta_p=0.732031 |
| turbine1_3_kacker_okapuu | error | only 0-dimensional arrays can be converted to Python scalars |
| turbine1_3_original | error | adjust_streamlines() missing 1 required positional argument: 'massflow_fraction' |
| turbine1_3_td2 | error | nan detected |
| turbine1_3_traupel | error |  ******************************************************************************* CanteraError thrown by Phase::setTemperature: temperature must be positive. T = -nan **************************************************************** |
| turbine1_5_fixed_streamlines | completed | P=3395.099 kW; PR=3.388027; row mdot spread=0.00522%; eta_p=0.732401 |
| turbine1_5_original | error | adjust_streamlines() missing 1 required positional argument: 'massflow_fraction' |
| turbine1_5_td2 | error | nan detected |
| turbine1_9_fixed_streamlines | completed | P=3396.131 kW; PR=3.389151; row mdot spread=0.00337%; eta_p=0.732570 |
| turbine1_9_original | error | adjust_streamlines() missing 1 required positional argument: 'massflow_fraction' |
| turbine1_9_td2 | error | nan detected |
| turbine1_angle | error | adjust_streamlines() missing 1 required positional argument: 'massflow_fraction' |
| turbine1_angle_fixed_streamlines | completed | P=4037.833 kW; PR=2.750594; row mdot spread=0.00006%; eta_p=0.645311 |
| turbine1_cooling | error | adjust_streamlines() missing 1 required positional argument: 'massflow_fraction' |
| turbine1_cooling_fixed_streamlines | completed | P=3397.723 kW; PR=3.383277; row mdot spread=0.00398%; eta_p=0.717168 |
| turbine1_offdesign | error | adjust_streamlines() missing 1 required positional argument: 'massflow_fraction' |
| turbine1_repeat | error | adjust_streamlines() missing 1 required positional argument: 'massflow_fraction' |
| turbine1_repeat_fixed_streamlines | completed | P=3394.089 kW; PR=3.385441; row mdot spread=0.00202%; eta_p=0.732031 |
| turbine2_17_fixed_streamlines | completed | P=11119.904 kW; PR=3.779648; row mdot spread=3.18776%; eta_p=0.782467 |
| turbine2_17_original | error | adjust_streamlines() missing 1 required positional argument: 'massflow_fraction' |
| turbine2_17_td2 | error | nan detected |
| turbine2_1_fixed_streamlines | completed | P=11156.166 kW; PR=3.833255; row mdot spread=0.00465%; eta_p=0.785322 |
| turbine2_1_original | error | adjust_streamlines() missing 1 required positional argument: 'massflow_fraction' |
| turbine2_1_td2 | error | nan detected |
| turbine2_3_fixed_streamlines | completed | P=11118.565 kW; PR=3.814960; row mdot spread=0.00576%; eta_p=0.783666 |
| turbine2_3_original | error | adjust_streamlines() missing 1 required positional argument: 'massflow_fraction' |
| turbine2_3_td2 | error | nan detected |
| turbine2_5_fixed_streamlines | completed | P=11124.919 kW; PR=3.819942; row mdot spread=0.00458%; eta_p=0.784155 |
| turbine2_5_original | error | adjust_streamlines() missing 1 required positional argument: 'massflow_fraction' |
| turbine2_5_td2 | error | nan detected |
| turbine2_9_fixed_streamlines | completed | P=11130.458 kW; PR=3.822300; row mdot spread=0.00629%; eta_p=0.784376 |
| turbine2_9_original | error | adjust_streamlines() missing 1 required positional argument: 'massflow_fraction' |
| turbine2_9_td2 | error | nan detected |
| turbine2_counterrotation | error | adjust_streamlines() missing 1 required positional argument: 'massflow_fraction' |
| turbine2_counterrotation_fixed_streamlines | completed | P=9208.248 kW; PR=1.530492; row mdot spread=0.00530%; eta_p=0.226166 |

## py312_numpy126

{"counts": {"error": 7}, "cases": 7, "median_process_elapsed_seconds": 0.5225541999971028, "maximum_process_elapsed_seconds": 1.1953099000020302, "max_peak_working_set_bytes": 89452544}

| Case | Observed status | Result / diagnostic |
|---|---|---|
| turbine1_3_ainley_mathieson | error | module 'numpy' has no attribute 'long' |
| turbine1_3_craig_cox | error | module 'numpy' has no attribute 'long' |
| turbine1_3_fixed_streamlines | error | module 'numpy' has no attribute 'long' |
| turbine1_3_kacker_okapuu | error | module 'numpy' has no attribute 'long' |
| turbine1_3_original | error | module 'numpy' has no attribute 'long' |
| turbine1_3_td2 | error | module 'numpy' has no attribute 'long' |
| turbine1_3_traupel | error | module 'numpy' has no attribute 'long' |

