"""Run the Mattingly 9.1 single-stage axial compressor case."""
import math
from sunimuhendis import make_env

def build_case():
    p0=14.7*6894.76; t0=518.7/1.8; mass=50*.453592; rpm=1000*30/math.pi; mean=.3048; cax=.0254
    areas=[207.2/39.3701**2,179.1/39.3701**2,165.3/39.3701**2]; heights=[a/(math.pi*4*mean) for a in areas]
    stations=[{"axial_m":i*cax,"hub_radius_m":mean-h,"shroud_radius_m":mean+h} for i,h in enumerate(heights)]
    design={"machine_type":"compressor","flow_path":"axial","passage":{"stations":stations},"rows":[{"row_id":"inlet","row_type":"inlet","axial_location_m":0.0},{"row_id":"rotor_1","stage_id":"stage_1","row_type":"rotor","axial_location_m":cax,"blade_count":40,"axial_chord_m":cax,"metal_angle_out_deg":{"points":[{"span_fraction":0.0,"value":-23.87},{"span_fraction":1.0,"value":-23.87}]}},{"row_id":"stator_1","stage_id":"stage_1","row_type":"stator","axial_location_m":2*cax,"blade_count":40,"axial_chord_m":cax,"metal_angle_out_deg":{"points":[{"span_fraction":0.0,"value":40.0},{"span_fraction":1.0,"value":40.0}]}},{"row_id":"outlet","row_type":"outlet","axial_location_m":2*cax}]}
    task={"operating_conditions":{"mass_flow_kg_s":mass,"inlet_total_pressure_pa":p0,"inlet_total_temperature_k":t0,"shaft_speed_rpm":rpm,"inlet_mach":.7,"inlet_flow_angle_deg":40.0,"outlet_total_pressure_pa":1.3*p0},"physics":{"default_loss_model":"fixed_pressure","fixed_pressure_loss_fraction":0.0},"numerics":{"streamlines":3}}
    return design,task

if __name__=="__main__":
    d,t=build_case(); print(make_env("turbomachinery_throughflow").evaluate("compressor_demo",t,"mattingly_9_1",d).model_dump_json(indent=2))
