import pytest
from src.parsing.json_parser import parse_llm_json

def test_parse_valid_json():
    raw = '{"key": "value"}'
    res = parse_llm_json(raw)
    assert res["key"] == "value"

def test_parse_markdown_json():
    raw = "```json\n{\"key\": 123}\n```"
    res = parse_llm_json(raw)
    assert res["key"] == 123

def test_parse_broken_json():
    # missing closing brace and quote
    raw = '{"key": "value'
    res = parse_llm_json(raw)
    assert res["key"] == "value"

def test_parse_list_return():
    raw = '[{"key": "value"}]'
    res = parse_llm_json(raw)
    assert res["key"] == "value"
