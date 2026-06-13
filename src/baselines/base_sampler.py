from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseSampler(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def sample(self, num_samples: int) -> List[Dict[str, Any]]:
        pass
