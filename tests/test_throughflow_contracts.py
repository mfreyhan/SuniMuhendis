import pytest
from pydantic import ValidationError
from sunimuhendis.environments.turbomachinery_throughflow import ThroughflowDesignV1, ThroughflowTaskV1, ThroughflowSimulationResultV1
from sunimuhendis import list_environments, make_env

def design(n=1):
    rows=[{"row_id":"in","row_type":"inlet","axial_location_m":0.0}]
    for i in range(n):
        rows += [{"row_id":f"s{i}","stage_id":f"st{i}","row_type":"stator","axial_location_m":.1+2*i,"blade_count":30,"axial_chord_m":.02},{"row_id":f"r{i}","stage_id":f"st{i}","row_type":"rotor","axial_location_m":.2+2*i,"blade_count":40,"axial_chord_m":.03}]
    rows += [{"row_id":"out","row_type":"outlet","axial_location_m":.3+2*(n-1)}]
    return {"machine_type":"turbine","flow_path":"axial","passage":{"stations":[{"axial_m":0.0,"hub_radius_m":.2,"shroud_radius_m":.3},{"axial_m":5.0,"hub_radius_m":.2,"shroud_radius_m":.3}]},"rows":rows}
def task(**kw):
    value={"operating_conditions":{"mass_flow_kg_s":12.0,"inlet_total_pressure_pa":300000.0,"inlet_total_temperature_k":900.0,"shaft_speed_rpm":12000.0},"physics":{"default_loss_model":"diffusion"},"numerics":{"streamlines":9}}
    value.update(kw); return value

@pytest.mark.parametrize("n",[1,2,6])
def test_single_and_multistage(n): assert ThroughflowDesignV1.model_validate(design(n)).stage_count==n
def test_resolution_and_row_loss_are_task_owned():
    d=ThroughflowDesignV1.model_validate(design(2)); t=ThroughflowTaskV1.model_validate(task(physics={"default_loss_model":"td2","row_loss_models":{"r1":"diffusion"}},numerics={"streamlines":17},max_stages=2)); t.validate_design_ownership(d)
def test_unknown_loss_row_is_rejected():
    t=ThroughflowTaskV1.model_validate(task(physics={"default_loss_model":"diffusion","row_loss_models":{"missing":"td2"}}))
    with pytest.raises(ValueError,match="unknown rows"): t.validate_design_ownership(ThroughflowDesignV1.model_validate(design()))
def test_fixed_loss_requires_explicit_fraction():
    parsed=ThroughflowTaskV1.model_validate(task(physics={"default_loss_model":"fixed_pressure"}))
    with pytest.raises(ValueError,match="requires a fraction"): parsed.validate_design_ownership(ThroughflowDesignV1.model_validate(design()))
def test_extra_fields_are_rejected():
    value=design(); value["rows"][0]["unknown"]=1
    with pytest.raises(ValidationError): ThroughflowDesignV1.model_validate(value)
def test_numerical_failure_is_not_reward_eligible():
    with pytest.raises(ValidationError,match="clean success"): ThroughflowSimulationResultV1.model_validate({"status":"success","reward_eligible":True,"diagnostics":[{"category":"numerical_failure","code":"massflow","message":"spread exceeded"}]})

def test_environment_is_registered_and_lazy():
    assert "turbomachinery_throughflow" in list_environments()
    env=make_env("turbomachinery_throughflow")
    assert env.simulator.VERSION=="nasa_turbo_design_experimental_v1"
