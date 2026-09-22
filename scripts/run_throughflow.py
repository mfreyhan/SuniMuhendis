"""Run a one- or two-stage axial turbine through the public API."""
import argparse
from sunimuhendis import make_env

def build_case(stages):
    if stages not in (1,2): raise ValueError("demo supports 1 or 2 stages")
    h1=.04; h2=1.159*h1; h3=1.317*h2
    heights=[h1,h1,h2,h3] if stages==1 else [h1,h1,h2,h3,1.1*h3,1.21*h3]
    cax=(h1+h2+h3)/3; mean=.389
    stations=[{"axial_m":i*cax,"hub_radius_m":mean-h/2,"shroud_radius_m":mean+h/2} for i,h in enumerate(heights)]
    rows=[{"row_id":"inlet","row_type":"inlet","axial_location_m":0.0}]
    angles=[(73.0,-67.6),(70.0,-65.0)]
    for i in range(stages):
        stage=f"stage_{i+1}"; sx=(2+2*i)*cax; rx=(3+2*i)*cax
        rows += [{"row_id":f"stator_{i+1}","stage_id":stage,"row_type":"stator","axial_location_m":sx,"blade_count":40,"axial_chord_m":cax,"metal_angle_out_deg":{"points":[{"span_fraction":0.0,"value":angles[i][0]},{"span_fraction":1.0,"value":angles[i][0]}]}},{"row_id":f"rotor_{i+1}","stage_id":stage,"row_type":"rotor","axial_location_m":rx,"blade_count":50,"axial_chord_m":cax,"tip_clearance_m":.0005,"metal_angle_out_deg":{"points":[{"span_fraction":0.0,"value":angles[i][1]},{"span_fraction":1.0,"value":angles[i][1]}]}}]
    rows.append({"row_id":"outlet","row_type":"outlet","axial_location_m":stations[-1]["axial_m"]})
    design={"machine_type":"turbine","flow_path":"axial","passage":{"stations":stations},"rows":rows}
    if stages==1: mass,p0,t0,rpm,pout=35.9,500000.0,676.3,7500.0,500000.0/3.96
    else: mass,p0,t0,rpm,pout=22.0,1000000.0,1300.0,7500.0,1000000.0/4.45
    fractions={}
    for i in range(stages): fractions[f"stator_{i+1}"]=.221 if stages==1 else .15; fractions[f"rotor_{i+1}"]=.30 if stages==1 else .18
    task={"physics_profile":"optturb_turbine_regression_v1","operating_conditions":{"mass_flow_kg_s":mass,"inlet_total_pressure_pa":p0,"inlet_total_temperature_k":t0,"shaft_speed_rpm":rpm,"outlet_static_pressure_pa":pout},"physics":{"default_loss_model":"fixed_pressure","row_fixed_pressure_loss_fractions":fractions},"numerics":{"streamlines":5 if stages==2 else 3}}
    return design,task

if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--stages",type=int,choices=(1,2),default=1); args=parser.parse_args()
    design,task=build_case(args.stages)
    result=make_env("turbomachinery_throughflow").evaluate("throughflow_demo",task,f"axial_turbine_{args.stages}",design)
    print(result.model_dump_json(indent=2))
