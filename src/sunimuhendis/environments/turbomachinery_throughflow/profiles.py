"""Versioned evaluator-owned physics policies for throughflow tasks."""

from dataclasses import dataclass
from typing import FrozenSet, Optional, Tuple


@dataclass(frozen=True)
class ThroughflowPhysicsProfile:
    """A frozen policy boundary between an LLM design and the evaluator physics."""

    profile_id: str
    machine_type: Optional[str]
    flow_path: str
    maturity: str
    backend_revision: str
    nominal_loss_model: Optional[str]
    allowed_loss_models: FrozenSet[str]
    shadow_loss_models: Tuple[str, ...] = ()
    reward_enabled: bool = False
    purpose: str = ""

    def validate(self, design, physics) -> None:
        if self.machine_type is not None and design.machine_type != self.machine_type:
            raise ValueError(
                "physics profile {} requires machine_type={}".format(
                    self.profile_id, self.machine_type
                )
            )
        if design.flow_path != self.flow_path:
            raise ValueError(
                "physics profile {} requires flow_path={}".format(
                    self.profile_id, self.flow_path
                )
            )

        selected = {physics.default_loss_model, *physics.row_loss_models.values()}
        if not selected.issubset(self.allowed_loss_models):
            raise ValueError(
                "physics profile {} does not allow loss models {}".format(
                    self.profile_id,
                    sorted(selected - self.allowed_loss_models),
                )
            )
        if (
            self.nominal_loss_model is not None
            and physics.default_loss_model != self.nominal_loss_model
        ):
            raise ValueError(
                "physics profile {} requires default_loss_model={}".format(
                    self.profile_id, self.nominal_loss_model
                )
            )

    def provenance(self) -> dict[str, object]:
        return {
            "profile_id": self.profile_id,
            "maturity": self.maturity,
            "backend_revision": self.backend_revision,
            "nominal_loss_model": self.nominal_loss_model,
            "shadow_loss_models": list(self.shadow_loss_models),
            "reward_enabled": self.reward_enabled,
        }


_ALL_LOSS_MODELS = frozenset(
    {"fixed_pressure", "diffusion", "td2", "kacker_okapuu", "ainley_mathieson"}
)
_PINNED_NASA_REVISION = "23c2b0bf781b4b030014f458ecfde872896777a2"


PHYSICS_PROFILES = {
    "experimental_custom_v1": ThroughflowPhysicsProfile(
        profile_id="experimental_custom_v1",
        machine_type=None,
        flow_path="axial",
        maturity="experimental",
        backend_revision=_PINNED_NASA_REVISION,
        nominal_loss_model=None,
        allowed_loss_models=_ALL_LOSS_MODELS,
        purpose="Adapter development only; never produces training reward.",
    ),
    "mattingly_compressor_regression_v1": ThroughflowPhysicsProfile(
        profile_id="mattingly_compressor_regression_v1",
        machine_type="compressor",
        flow_path="axial",
        maturity="regression_only",
        backend_revision=_PINNED_NASA_REVISION,
        nominal_loss_model="fixed_pressure",
        allowed_loss_models=frozenset({"fixed_pressure"}),
        purpose="Pins the upstream Mattingly example; not physical validation.",
    ),
    "optturb_turbine_regression_v1": ThroughflowPhysicsProfile(
        profile_id="optturb_turbine_regression_v1",
        machine_type="turbine",
        flow_path="axial",
        maturity="regression_only",
        backend_revision=_PINNED_NASA_REVISION,
        nominal_loss_model="fixed_pressure",
        allowed_loss_models=frozenset({"fixed_pressure"}),
        purpose="Pins the upstream OptTurb example; not physical validation.",
    ),
    "axial_compressor_candidate_v1": ThroughflowPhysicsProfile(
        profile_id="axial_compressor_candidate_v1",
        machine_type="compressor",
        flow_path="axial",
        maturity="candidate",
        backend_revision=_PINNED_NASA_REVISION,
        nominal_loss_model="diffusion",
        allowed_loss_models=frozenset({"diffusion"}),
        purpose="Candidate nominal profile pending Stage 35 physical validation.",
    ),
    "axial_turbine_candidate_v1": ThroughflowPhysicsProfile(
        profile_id="axial_turbine_candidate_v1",
        machine_type="turbine",
        flow_path="axial",
        maturity="candidate",
        backend_revision=_PINNED_NASA_REVISION,
        nominal_loss_model="kacker_okapuu",
        allowed_loss_models=frozenset({"kacker_okapuu"}),
        shadow_loss_models=("td2", "ainley_mathieson"),
        purpose="Candidate nominal profile pending independent turbine validation.",
    ),
}


def get_physics_profile(profile_id: str) -> ThroughflowPhysicsProfile:
    try:
        return PHYSICS_PROFILES[profile_id]
    except KeyError as exc:
        raise ValueError("unknown throughflow physics profile: {}".format(profile_id)) from exc
