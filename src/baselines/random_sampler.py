import random
from typing import Dict, Any, List
from .base_sampler import BaseSampler

class RandomSampler(BaseSampler):
    def __init__(self):
        super().__init__("RandomSampler")

    def sample(self, num_samples: int) -> List[Dict[str, Any]]:
        designs = []
        for _ in range(num_samples):
            geo_type = random.choice(["concentric_tube", "shell_and_tube"])
            design = {
                "geometry_type": geo_type,
                "length": random.uniform(0.1, 10.0),
                "inner_tube_di": random.uniform(0.005, 0.1),
                "inner_tube_do": random.uniform(0.005, 0.1),
                "outer_shell_di": random.uniform(0.05, 1.0),
                "number_of_tubes": random.randint(1, 200),
                "baffle_spacing": random.uniform(0.0, 2.0)
            }
            designs.append(design)
        return designs
