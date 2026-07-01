import os
import time
from typing import Any, Dict, Optional

from src.model_clients.base import BaseModelClient

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

class OpenRouterClient(BaseModelClient):
    """
    OpenRouter API (OpenAI uyumlu) üzerinden model çağıran istemci.
    Token `.env`/ortamdaki `OPENROUTER_API_KEY`'dan okunur.
    """

    def __init__(
        self,
        model: str,
        name: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        api_key_env: str = "OPENROUTER_API_KEY",
        base_url: str = OPENROUTER_BASE_URL,
        timeout: float = 600.0,
    ):
        super().__init__(name or model)
        self.model = model
        self.params = params or {}

        self.last_latency_ms: float = 0.0
        self.last_prompt_tokens: Optional[int] = None
        self.last_completion_tokens: Optional[int] = None

        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise RuntimeError(
                f"{api_key_env} bulunamadı. `.env` dosyasına {api_key_env} ekleyin."
            )

        try:
            from openai import OpenAI
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install openai") from e

        # OpenRouter önerisi: Headers ile HTTP-Referer ve X-Title göndermek.
        default_headers = {
            "HTTP-Referer": "https://github.com/SuniMuhendis", # Sitenizin adresi veya depo linki
            "X-Title": "Heat Exchanger Benchmark"
        }

        self._client = OpenAI(
            base_url=base_url, 
            api_key=api_key, 
            timeout=timeout,
            default_headers=default_headers
        )

    def generate_design(self, prompt: str) -> str:
        start = time.perf_counter()
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            **self.params,
        )
        self.last_latency_ms = (time.perf_counter() - start) * 1000

        if resp.usage:
            self.last_prompt_tokens = getattr(resp.usage, "prompt_tokens", None)
            self.last_completion_tokens = getattr(resp.usage, "completion_tokens", None)

        return resp.choices[0].message.content or ""
