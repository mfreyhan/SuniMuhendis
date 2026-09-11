import os
import pytest
from unittest.mock import MagicMock, patch

from sunimuhendis.model_clients.openrouter_client import OpenRouterClient
from scripts.sync_openrouter import prune_openrouter_models


def test_prune_openrouter_models():
    api_models = [
        {"id": "meta-llama/llama-3.3-70b-instruct"},
        {"id": "google/gemma-4-31b-it:free"},
        {"id": "openai/gpt-oss-20b"},
    ]

    existing = [
        # Dead free model whose base model exists in api_models
        {"name": "llama-3.3-70b-instruct", "model": "meta-llama/llama-3.3-70b-instruct:free"},
        # Live free model
        {"name": "gemma-4-31b-it", "model": "google/gemma-4-31b-it:free"},
        # Completely dead model
        {"name": "dead-model", "model": "some/dead-model:free"},
        # Duplicate of live model
        {"name": "gpt-oss-20b", "model": "openai/gpt-oss-20b"},
        {"name": "gpt-oss-20b-dup", "model": "openai/gpt-oss-20b"},
    ]

    kept, pruned, converted = prune_openrouter_models(existing, api_models)

    # 1. llama-3.3-70b-instruct:free should be converted to meta-llama/llama-3.3-70b-instruct
    assert ("meta-llama/llama-3.3-70b-instruct:free", "meta-llama/llama-3.3-70b-instruct") in converted
    # 2. dead-model should be pruned
    assert "some/dead-model:free" in pruned
    # 3. Duplicate should be pruned or skipped
    kept_ids = [m["model"] for m in kept]
    assert "meta-llama/llama-3.3-70b-instruct" in kept_ids
    assert "google/gemma-4-31b-it:free" in kept_ids
    assert "openai/gpt-oss-20b" in kept_ids
    assert kept_ids.count("openai/gpt-oss-20b") == 1
    assert "some/dead-model:free" not in kept_ids


@patch.dict(os.environ, {"OPENROUTER_API_KEY": "fake_test_key"})
def test_openrouter_client_404_free_fallback():
    client = OpenRouterClient(model="meta-llama/llama-3.3-70b-instruct:free", max_retries=2)

    # Mock completion response
    mock_choice = MagicMock()
    mock_choice.message.content = '{"geometry_type": "concentric_tube"}'
    mock_success_resp = MagicMock()
    mock_success_resp.choices = [mock_choice]
    mock_success_resp.usage = None

    # 1st call raises 404 (unavailable for free), 2nd call succeeds
    error_msg = "NotFoundError: Error code: 404 - This model is unavailable for free. The paid version is available now - use this slug instead: meta-llama/llama-3.3-70b-instruct"
    client._client.chat.completions.create = MagicMock(
        side_effect=[Exception(error_msg), mock_success_resp]
    )

    result = client.generate_design("test prompt")

    assert result == '{"geometry_type": "concentric_tube"}'
    # Model should have fallen back to the non-free slug
    assert client.model == "meta-llama/llama-3.3-70b-instruct"
    assert client._client.chat.completions.create.call_count == 2


@patch.dict(os.environ, {"OPENROUTER_API_KEY": "fake_test_key"})
def test_openrouter_client_429_retry():
    client = OpenRouterClient(model="google/gemma-4-31b-it:free", max_retries=3, backoff_factor=0.01)

    mock_choice = MagicMock()
    mock_choice.message.content = '{"geometry_type": "shell_and_tube"}'
    mock_success_resp = MagicMock()
    mock_success_resp.choices = [mock_choice]
    mock_success_resp.usage = None

    # 1st call raises 429, 2nd call succeeds
    error_msg = "RateLimitError: Error code: 429 - provider returned error"
    client._client.chat.completions.create = MagicMock(
        side_effect=[Exception(error_msg), mock_success_resp]
    )

    result = client.generate_design("test prompt")

    assert result == '{"geometry_type": "shell_and_tube"}'
    assert client._client.chat.completions.create.call_count == 2
