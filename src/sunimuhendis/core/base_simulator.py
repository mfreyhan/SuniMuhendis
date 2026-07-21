from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple

class BaseSimulator(ABC):
    """
    Base class from which all simulators inherit.
    """
    
    @abstractmethod
    def simulate(self, design_params: Dict[str, Any]) -> Tuple[bool, Dict[str, float], Dict[str, Any], str]:
        """
        Takes design parameters and runs the simulation.
        
        Args:
            design_params: Design parameters (must have passed DRC).
            
        Returns:
            Tuple:
                - success (bool): Whether the simulation completed without crashing.
                - metrics (Dict[str, float]): Basic engineering metrics outputted by the simulator.
                - raw_data (Dict[str, Any]): Other data produced by the simulator.
                - error_message (str): error message if success=False, otherwise empty string "".
        """
        pass
