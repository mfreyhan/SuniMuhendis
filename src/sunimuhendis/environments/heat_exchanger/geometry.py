"""Shared geometry helpers for the heat-exchanger environment."""

from typing import Dict

import ht


DEFAULT_TUBE_PASSES = 2
DEFAULT_PITCH_RATIO = 1.25
DEFAULT_PITCH_TYPE = "square"

PITCH_ANGLES: Dict[str, int] = {
    "triangular": 30,
    "30deg": 30,
    "60deg": 60,
    "square": 90,
    "45deg": 45,
    "90deg": 90,
}


def pitch_angle(pitch_type: str) -> int:
    """Return the tube-layout angle understood by ``ht``."""
    try:
        return PITCH_ANGLES[pitch_type]
    except KeyError:
        raise ValueError("Unsupported pitch type: {!r}".format(pitch_type))


def bundle_diameter(
    number_of_tubes: int,
    tube_outer_diameter: float,
    pitch: float,
    tube_passes: int,
    pitch_type: str,
) -> float:
    """Calculate the physical diameter of the complete tube bundle."""
    return float(
        ht.size_bundle_from_tubecount(
            N=number_of_tubes,
            Do=tube_outer_diameter,
            pitch=pitch,
            Ntp=tube_passes,
            angle=pitch_angle(pitch_type),
            Method="Phadkeb",
        )
    )


def available_bundle_diameter(shell_inner_diameter: float) -> float:
    """Return shell ID less the recommended shell-to-bundle clearance."""
    clearance = float(ht.shell_clearance(DShell=shell_inner_diameter))
    return max(shell_inner_diameter - clearance, 0.0)
