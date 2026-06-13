from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple

class BaseSimulator(ABC):
    """
    Tüm simülatörlerin türeyeceği temel sınıf.
    """
    
    @abstractmethod
    def simulate(self, design_params: Dict[str, Any]) -> Tuple[bool, Dict[str, float], Dict[str, Any], str]:
        """
        Tasarım parametrelerini alıp simülasyonu çalıştırır.
        
        Args:
            design_params: Tasarım parametreleri (DRC'den geçmiş olmalıdır).
            
        Returns:
            Tuple:
                - success (bool): Simülasyonun çökmeden tamamlanıp tamamlanmadığı.
                - metrics (Dict[str, float]): Simülatörden çıkan temel mühendislik metrikleri.
                - raw_data (Dict[str, Any]): Simülatörün ürettiği diğer veriler.
                - error_message (str): success=False ise hata mesajı, yoksa boş string "".
        """
        pass
