import random
from typing import Dict, Any, List
from scipy.stats import qmc
from .base_sampler import BaseSampler

class LatinHypercubeSampler(BaseSampler):
    def __init__(self):
        super().__init__("LatinHypercubeSampler")
        
    def sample(self, num_samples: int) -> List[Dict[str, Any]]:
        # 6 continuous dimensions
        sampler = qmc.LatinHypercube(d=6)
        sample_points = sampler.random(n=num_samples)
        
        # Define bounds: [min, max]
        bounds = [
            [0.1, 10.0],   # length
            [0.005, 0.1],  # inner_di
            [0.005, 0.15], # inner_do
            [0.05, 1.0],   # shell_di
            [1, 200],      # num_tubes
            [0.0, 2.0]     # baffle_spacing
        ]
        
        designs = []
        for i in range(num_samples):
            p = sample_points[i]
            length = bounds[0][0] + p[0]*(bounds[0][1] - bounds[0][0])
            inner_di = bounds[1][0] + p[1]*(bounds[1][1] - bounds[1][0])
            inner_do = bounds[2][0] + p[2]*(bounds[2][1] - bounds[2][0])
            shell_di = bounds[3][0] + p[3]*(bounds[3][1] - bounds[3][0])
            num_tubes = int(bounds[4][0] + p[4]*(bounds[4][1] - bounds[4][0]))
            baffle_spacing = bounds[5][0] + p[5]*(bounds[5][1] - bounds[5][0])
            
            geo_type = "shell_and_tube" if num_tubes > 1 else "concentric_tube"
            
            design = {
                "geometry_type": geo_type,
                "length": length,
                "inner_tube_di": inner_di,
                "inner_tube_do": inner_do,
                "outer_shell_di": shell_di,
                "number_of_tubes": num_tubes,
                "baffle_spacing": baffle_spacing
            }
            designs.append(design)
            
        return designs
