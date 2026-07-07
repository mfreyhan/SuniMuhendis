import random
import math
from typing import Dict, Any, List
from .base_sampler import BaseSampler

class HeuristicSampler(BaseSampler):
    def __init__(self):
        super().__init__("HeuristicSampler")

    def sample(self, num_samples: int) -> List[Dict[str, Any]]:
        designs = []
        for _ in range(num_samples):
            geo_type = random.choice(["concentric_tube", "shell_and_tube"])
            
            # Use basic heuristics to ensure higher chance of valid geometries
            di = random.uniform(0.01, 0.05)
            # Outer diameter is always slightly larger than inner
            do = di + random.uniform(0.002, 0.01)
            
            if geo_type == "concentric_tube":
                num_tubes = 1
                shell_di = do + random.uniform(0.01, 0.1)
                baffle_spacing = 0.0
            else:
                num_tubes = random.randint(2, 100)
                # Ensure shell is big enough for tubes approximately (max 50% fill)
                min_shell_area = (num_tubes * math.pi * (do/2)**2) / 0.5 
                min_shell_di = 2 * math.sqrt(min_shell_area / math.pi)
                shell_di = random.uniform(min_shell_di, min_shell_di + 0.5)
                baffle_spacing = random.uniform(0.1, 1.0)
                
            length = random.uniform(1.0, 6.0)
            if baffle_spacing > length:
                baffle_spacing = length / 5.0
                
            design = {
                "geometry_type": geo_type,
                "length": length,
                "inner_tube_di": di,
                "inner_tube_do": do,
                "outer_shell_di": shell_di,
                "number_of_tubes": num_tubes,
                "baffle_spacing": baffle_spacing
            }
            designs.append(design)
        return designs
