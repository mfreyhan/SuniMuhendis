from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from .types import RewardResult

class BaseRewardFunction(ABC):
    """
    Tüm reward fonksiyonlarının türeyeceği temel sınıf.
    """
    
    @abstractmethod
    def calculate_reward(
        self, 
        task_params: Dict[str, Any],
        metrics: Dict[str, Any], 
        is_valid: bool = True, 
        error_message: Optional[str] = None
    ) -> RewardResult:
        """
        Simülatör çıktıları veya hatalarından reward hesaplar.
        
        Args:
            task_params: Tasarımın hedeflerini veya ortam parametrelerini içerir.
            metrics: Simülasyondan dönen metrikler (is_valid=True ise).
            is_valid: Tasarımın veya simülasyonun geçerli/başarılı olup olmadığı.
            error_message: Hata durumunda mesaj.
            
        Returns:
            RewardResult: Normalize edilmiş ve bileşenlerine ayrılmış reward nesnesi.
        """
        pass
