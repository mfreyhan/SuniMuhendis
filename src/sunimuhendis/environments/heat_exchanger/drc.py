from typing import Dict, Any, Tuple, Optional

from .geometry import (
    DEFAULT_PITCH_RATIO,
    DEFAULT_PITCH_TYPE,
    DEFAULT_TUBE_PASSES,
    available_bundle_diameter,
    bundle_diameter,
)

def run_heat_exchanger_drc(design_params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Simülasyon öncesi geometrik kuralları kontrol eder (DRC).
    """
    geo_type = design_params.get("geometry_type")
    
    di = design_params.get("inner_tube_di", 0)
    do = design_params.get("inner_tube_do", 0)
    shell_di = design_params.get("outer_shell_di", 0)
    length = design_params.get("length", 0)
    num_tubes = design_params.get("number_of_tubes", 1)
    baffle_spacing = design_params.get("baffle_spacing", 0)
    
    if di >= do:
        return False, "DRC Error: Inner tube inner diameter cannot be greater than or equal to its outer diameter."
        
    if geo_type == "concentric_tube":
        if num_tubes != 1:
            return False, "DRC Error: Number of tubes must be 1 for concentric tube type."
        if do >= shell_di:
            return False, "DRC Error: Inner tube outer diameter cannot be greater than or equal to outer tube inner diameter."
            
    elif geo_type == "shell_and_tube":
        if num_tubes < 2:
            return False, "DRC Error: Number of tubes must be at least 2 for shell and tube type."
        if num_tubes % DEFAULT_TUBE_PASSES != 0:
            return False, "DRC Error: Number of tubes must be divisible by the number of tube passes (2)."
        
        if do >= shell_di:
            return False, "DRC Error: Tube outer diameter cannot be greater than or equal to shell inner diameter."
        if baffle_spacing <= 0:
            return False, "DRC Error: Baffle spacing must be positive for shell and tube type."
        if baffle_spacing >= length:
            return False, "DRC Error: Baffle spacing must be smaller than the total length."

        pitch = do * DEFAULT_PITCH_RATIO
        try:
            required_bundle = bundle_diameter(
                num_tubes,
                do,
                pitch,
                DEFAULT_TUBE_PASSES,
                DEFAULT_PITCH_TYPE,
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
