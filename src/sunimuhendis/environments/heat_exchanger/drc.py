from typing import Dict, Any, Tuple, Optional

from .geometry import (
    DEFAULT_PITCH_RATIO,
    DEFAULT_PITCH_TYPE,
    DEFAULT_TUBE_PASSES,
    PITCH_ANGLES,
    available_bundle_diameter,
    bundle_diameter,
)

def run_heat_exchanger_drc(design_params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Checks geometric design rules before simulation (DRC).

    Layout parameters are read from the design itself, falling back to the same
    defaults the simulator uses. Reading them here (rather than assuming the
    defaults) keeps DRC and simulation agreeing about the same design: a design
    carrying e.g. ``tube_passes: 4`` must be judged against four passes in both
    places, or DRC passes a design the simulator then rejects.
    """
    geo_type = design_params.get("geometry_type")

    di = design_params.get("inner_tube_di", 0)
    do = design_params.get("inner_tube_do", 0)
    shell_di = design_params.get("outer_shell_di", 0)
    length = design_params.get("length", 0)
    num_tubes = design_params.get("number_of_tubes", 1)
    baffle_spacing = design_params.get("baffle_spacing", 0)

    tube_passes = design_params.get(
        "tube_passes",
        1 if geo_type == "concentric_tube" else DEFAULT_TUBE_PASSES,
    )
    pitch_type = design_params.get("pitch_type", DEFAULT_PITCH_TYPE)
    pitch_ratio = design_params.get("pitch_ratio", DEFAULT_PITCH_RATIO)

    if di >= do:
        return False, "DRC Error: Inner tube inner diameter cannot be greater than or equal to its outer diameter."

    if geo_type == "concentric_tube":
        if num_tubes != 1:
            return False, "DRC Error: Number of tubes must be 1 for concentric tube type."
        if do >= shell_di:
            return False, "DRC Error: Inner tube outer diameter cannot be greater than or equal to outer tube inner diameter."

    elif geo_type == "shell_and_tube":
        if not isinstance(tube_passes, int) or isinstance(tube_passes, bool) or tube_passes <= 0:
            return False, "DRC Error: Number of tube passes must be a positive integer."
        if tube_passes % 2 != 0:
            return False, "DRC Error: Number of tube passes must be even for shell and tube type."
        if pitch_type not in PITCH_ANGLES:
            return False, "DRC Error: Unsupported pitch type: {!r}.".format(pitch_type)
        if (not isinstance(pitch_ratio, (int, float)) or isinstance(pitch_ratio, bool)
                or pitch_ratio < 1.25):
            return False, "DRC Error: Pitch ratio must be at least 1.25 (TEMA minimum)."

        if num_tubes < 2:
            return False, "DRC Error: Number of tubes must be at least 2 for shell and tube type."
        if num_tubes < tube_passes:
            return False, (
                "DRC Error: Number of tubes ({}) cannot be fewer than the number of tube "
                "passes ({})."
            ).format(num_tubes, tube_passes)
        if num_tubes % tube_passes != 0:
            return False, (
                "DRC Error: Number of tubes must be divisible by the number of tube passes ({})."
            ).format(tube_passes)

        if do >= shell_di:
            return False, "DRC Error: Tube outer diameter cannot be greater than or equal to shell inner diameter."
        if baffle_spacing <= 0:
            return False, "DRC Error: Baffle spacing must be positive for shell and tube type."
        if baffle_spacing >= length:
            return False, "DRC Error: Baffle spacing must be smaller than the total length."

        pitch = do * pitch_ratio
        try:
            required_bundle = bundle_diameter(
                num_tubes,
                do,
                pitch,
                tube_passes,
                pitch_type,
            )
            available_bundle = available_bundle_diameter(shell_di)
        except (ValueError, ZeroDivisionError) as exc:
            return False, "DRC Error: Tube bundle geometry could not be evaluated: {}".format(exc)

        if required_bundle > available_bundle:
            return False, (
                "DRC Error: Tube bundle diameter {:.4f} m exceeds the available "
                "shell diameter {:.4f} m after clearance."
            ).format(required_bundle, available_bundle)

    return True, None
