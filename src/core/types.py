from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class RewardResult(BaseModel):
    """
    Simülasyon sonuçlarından hesaplanan normalize edilmiş ödül değerlerini tutar.
    """
    normalized_total: float = Field(..., description="Normalize edilmiş toplam reward.")
    components: Dict[str, float] = Field(default_factory=dict, description="Reward fonksiyonunun alt bileşenleri.")
    is_valid: bool = Field(..., description="Tasarımın fiziksel/şema olarak geçerli olup olmadığı.")
    error_message: Optional[str] = Field(None, description="Eğer is_valid False ise hata mesajı.")


class EvaluationResult(BaseModel):
    """
    BaseEnvironment'in döneceği nihai değerlendirme objesi.
    """
    task_id: str = Field(..., description="Değerlendirilen task'ın ID'si.")
    design_id: str = Field(default="unknown", description="Değerlendirilen tasarımın ID'si (varsa).")
    status: str = Field(..., description="'success', 'schema_error', 'drc_error', 'simulation_error'")
    error_message: Optional[str] = Field(None, description="Hata durumu mesajı")
    reward: RewardResult
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Simülatörden dönen ham mühendislik metrikleri.")
    raw_simulation_output: Dict[str, Any] = Field(default_factory=dict, description="Simülatörün dönebileceği diğer raw data (opsiyonel).")
