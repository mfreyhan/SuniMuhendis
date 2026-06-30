from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from .types import ScoreResult

class BaseScoreFunction(ABC):
    """
    Tüm score fonksiyonlarının türeyeceği temel sınıf.
    """
    
    @abstractmethod
    def calculate_score(
        self, 
        task_params: Dict[str, Any],
        metrics: Dict[str, Any], 
        is_valid: bool = True, 
        error_message: Optional[str] = None
    ) -> ScoreResult:
        """
        Simülatör çıktıları veya hatalarından score hesaplar.
        
        Args:
            task_params: Tasarımın hedeflerini veya ortam parametrelerini içerir.
            metrics: Simülasyondan dönen metrikler (is_valid=True ise).
            is_valid: Tasarımın veya simülasyonun geçerli/başarılı olup olmadığı.
            error_message: Hata durumunda mesaj.
            
        Returns:
            ScoreResult: Normalize edilmiş ve bileşenlerine ayrılmış score nesnesi.
        """
        pass
