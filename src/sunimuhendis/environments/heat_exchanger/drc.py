from typing import Dict, Any, Tuple, Optional

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
        
        if do >= shell_di:
            return False, "DRC Error: Tube outer diameter cannot be greater than or equal to shell inner diameter."
            
        import math
        total_tube_area = num_tubes * (math.pi * (do / 2)**2)
        shell_area = math.pi * (shell_di / 2)**2
        
        if total_tube_area > shell_area * 0.6:
            return False, "DRC Error: The area occupied by tubes cannot exceed 60% of the shell area."
            
        if baffle_spacing > length:
            return False, "DRC Error: Baffle spacing cannot exceed the total length."
            
    return True, None
