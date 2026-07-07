from pydantic import BaseModel, Field
from typing import Literal

class HeatExchangerDesign(BaseModel):
    """
    Heat Exchanger tasarım parametrelerini temsil eder.
    LLM'in bu formatta JSON üretmesi beklenmektedir.
    """
    geometry_type: Literal["concentric_tube", "shell_and_tube"] = Field(
        ..., description="'concentric_tube' veya 'shell_and_tube' olmalıdır."
    )
    length: float = Field(..., gt=0.0, description="Boru/Shell uzunluğu [m]")
    inner_tube_di: float = Field(..., gt=0.0, description="İç borunun iç çapı [m]")
    inner_tube_do: float = Field(..., gt=0.0, description="İç borunun dış çapı [m]")
    outer_shell_di: float = Field(..., gt=0.0, description="Dış kılıfın / shell'in iç çapı [m]")
    number_of_tubes: int = Field(
        default=1, ge=1, description="Boru sayısı (Concentric için 1, Shell-and-tube için > 1)"
    )
    baffle_spacing: float = Field(
        default=0.0, ge=0.0, description="Baffle aralığı [m] (Sadece Shell-and-tube için geçerli)"
    )
