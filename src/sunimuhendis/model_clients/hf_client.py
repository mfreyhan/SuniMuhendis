import os
import time
from typing import Any, Dict, Optional

from sunimuhendis.model_clients.base import BaseModelClient

# Hugging Face Inference Providers — OpenAI-compatible router (chat-completions).
HF_ROUTER_BASE_URL = "https://router.huggingface.co/v1"


class HFInferenceClient(BaseModelClient):
    """
    Client calling the model via Hugging Face Inference Providers.

    Since HF router is OpenAI-compatible, it uses the official `openai` SDK by
    changing the base_url. Token is read from `.env`/environment `HF_TOKEN`.

    Model id format: "owner/model" (e.g. "Qwen/Qwen2.5-32B-Instruct"); optional
    provider/policy suffix can be appended (":cheapest", ":together" etc.).

    `generate_design()` maintains the existing BaseModelClient contract; additional metadata
    can be read as attributes after the call:
      last_latency_ms, last_prompt_tokens, last_completion_tokens
    """

    def __init__(
        self,
        model: str,
        name: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        api_key_env: str = "HF_TOKEN",
        base_url: str = HF_ROUTER_BASE_URL,
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
                f"{api_key_env} not found. Add HF_TOKEN to .env file "
                f"(see .env.example) or provide it as an environment variable."
            )

        try:
            from openai import OpenAI
        except ImportError as e:  # pragma: no cover - environment dependent
            raise ImportError(
                "HFInferenceClient requires the 'openai' package: pip install openai"
            ) from e

        self._client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout)

    def generate_design(self, prompt: str) -> str:
        start = time.perf_counter()
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            **self.params,
        )
        self.last_latency_ms = (time.perf_counter() - start) * 1000.0

        usage = getattr(resp, "usage", None)
        self.last_prompt_tokens = getattr(usage, "prompt_tokens", None)
        self.last_completion_tokens = getattr(usage, "completion_tokens", None)

        return resp.choices[0].message.content or ""
