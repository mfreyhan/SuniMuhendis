import pytest
import json
from src.model_clients.dummy_random import DummyRandomClient
from src.parsing.json_parser import parse_llm_json

def test_dummy_random_client():
    client = DummyRandomClient()
    res_str = client.generate_design("some prompt")
    
    assert "```json" in res_str
    
    parsed = parse_llm_json(res_str)
    assert "geometry_type" in parsed
    assert "length" in parsed
