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
    nominal_deviation_model: Optional[str]
    allowed_deviation_models: FrozenSet[str]
    shadow_loss_models: Tuple[str, ...] = ()
    requires_complete_blade_geometry: bool = False
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

        selected_deviation = {
            physics.default_deviation_model,
            *physics.row_deviation_models.values(),
        }
        if not selected_deviation.issubset(self.allowed_deviation_models):
            raise ValueError(
                "physics profile {} does not allow deviation models {}".format(
                    self.profile_id,
                    sorted(selected_deviation - self.allowed_deviation_models),
                )
            )
        if (
            self.nominal_deviation_model is not None
            and physics.default_deviation_model != self.nominal_deviation_model
        ):
            raise ValueError(
                "physics profile {} requires default_deviation_model={}".format(
                    self.profile_id, self.nominal_deviation_model
                )
            )

        if self.requires_complete_blade_geometry:
            stage_rows = {}
            for row in design.rows:
                if row.row_type not in ("stator", "rotor"):
                    continue
                stage_rows.setdefault(row.stage_id, []).append(row)
                missing = []
                if row.stagger_angle_deg is None:
                    missing.append("stagger_angle_deg")
                if row.trailing_edge_thickness_m is None:
                    missing.append("trailing_edge_thickness_m")
                if row.row_type == "rotor" and row.tip_clearance_m is None:
                    missing.append("tip_clearance_m")
                if missing:
                    raise ValueError(
                        "physics profile {} requires {} for row {}".format(
                            self.profile_id, ", ".join(missing), row.row_id
                        )
                    )
            expected = ("rotor", "stator") if design.machine_type == "compressor" else ("stator", "rotor")
            for stage_id, rows in stage_rows.items():
                actual = tuple(row.row_type for row in rows)
                if actual != expected:
                    raise ValueError(
                        "physics profile {} requires {} row order in stage {}, got {}".format(
                            self.profile_id, expected, stage_id, actual
                        )
                    )

    def provenance(self) -> dict[str, object]:
        return {
            "profile_id": self.profile_id,
            "maturity": self.maturity,
            "backend_revision": self.backend_revision,
            "nominal_loss_model": self.nominal_loss_model,
            "nominal_deviation_model": self.nominal_deviation_model,
            "shadow_loss_models": list(self.shadow_loss_models),
            "reward_enabled": self.reward_enabled,
        }


_ALL_LOSS_MODELS = frozenset(
    {"fixed_pressure", "diffusion", "td2", "kacker_okapuu", "ainley_mathieson"}
)
_ALL_DEVIATION_MODELS = frozenset({"zero", "fixed", "carter"})
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
        nominal_deviation_model=None,
        allowed_deviation_models=_ALL_DEVIATION_MODELS,
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
        nominal_deviation_model="zero",
        allowed_deviation_models=frozenset({"zero"}),
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
        nominal_deviation_model="zero",
        allowed_deviation_models=frozenset({"zero"}),
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
        nominal_deviation_model="carter",
        allowed_deviation_models=frozenset({"carter"}),
        requires_complete_blade_geometry=True,
        purpose="Lieblein-style diffusion loss plus corrected Carter deviation; pending physical validation.",
    ),
    "axial_turbine_candidate_v1": ThroughflowPhysicsProfile(
        profile_id="axial_turbine_candidate_v1",
        machine_type="turbine",
        flow_path="axial",
        maturity="candidate",
        backend_revision=_PINNED_NASA_REVISION,
        nominal_loss_model="td2",
        allowed_loss_models=frozenset({"td2"}),
        nominal_deviation_model="zero",
        allowed_deviation_models=frozenset({"zero", "fixed"}),
        shadow_loss_models=("td2", "ainley_mathieson"),
        requires_complete_blade_geometry=True,
        purpose="Working NASA TD2 interim profile; Kacker-Okapuu remains a shadow model until upstream defects are fixed.",
    ),
}


def get_physics_profile(profile_id: str) -> ThroughflowPhysicsProfile:
    try:
        return PHYSICS_PROFILES[profile_id]
    except KeyError as exc:
        raise ValueError("unknown throughflow physics profile: {}".format(profile_id)) from exc
