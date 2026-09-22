"""Run one- or multi-stage axial compressors derived from Mattingly 9.1."""
import argparse
import math
from sunimuhendis import make_env

def build_case(stages=1,streamtubes=2):
    if stages<1: raise ValueError("stages must be positive")
    if streamtubes<1: raise ValueError("streamtubes must be positive")
    p0=14.7*6894.76; t0=518.7/1.8; mass=50*.453592; rpm=1000*30/math.pi; mean=.3048; cax=.0254
    areas=[207.2/39.3701**2,179.1/39.3701**2,165.3/39.3701**2]; heights=[a/(math.pi*4*mean) for a in areas]
    while len(heights)<2*stages+1: heights.append(heights[-1]*(heights[-1]/heights[-2]))
    stations=[{"axial_m":i*cax,"hub_radius_m":mean-h,"shroud_radius_m":mean+h} for i,h in enumerate(heights)]
    rows=[{"row_id":"inlet","row_type":"inlet","axial_location_m":0.0}]
    for i in range(stages):
        stage=f"stage_{i+1}"; rows += [{"row_id":f"rotor_{i+1}","stage_id":stage,"row_type":"rotor","axial_location_m":cax*(2*i+1),"blade_count":40,"axial_chord_m":cax,"metal_angle_out_deg":{"points":[{"span_fraction":0.0,"value":-23.87},{"span_fraction":1.0,"value":-23.87}]}},{"row_id":f"stator_{i+1}","stage_id":stage,"row_type":"stator","axial_location_m":cax*(2*i+2),"blade_count":40,"axial_chord_m":cax,"metal_angle_out_deg":{"points":[{"span_fraction":0.0,"value":40.0},{"span_fraction":1.0,"value":40.0}]}}]
    rows.append({"row_id":"outlet","row_type":"outlet","axial_location_m":2*stages*cax})
    design={"machine_type":"compressor","flow_path":"axial","passage":{"stations":stations},"rows":rows}
    task={"physics_profile":"mattingly_compressor_regression_v1","operating_conditions":{"mass_flow_kg_s":mass,"inlet_total_pressure_pa":p0,"inlet_total_temperature_k":t0,"shaft_speed_rpm":rpm,"inlet_mach":.7,"inlet_flow_angle_deg":40.0,"outlet_total_pressure_pa":1.3**stages*p0},"physics":{"default_loss_model":"fixed_pressure","fixed_pressure_loss_fraction":0.0},"numerics":{"streamlines":streamtubes+1}}
    return design,task

if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--stages",type=int,default=1); parser.add_argument("--streamtubes",type=int,default=2); args=parser.parse_args()
    d,t=build_case(args.stages,args.streamtubes); print(make_env("turbomachinery_throughflow").evaluate("compressor_demo",t,f"compressor_{args.stages}_stage",d).model_dump_json(indent=2))
