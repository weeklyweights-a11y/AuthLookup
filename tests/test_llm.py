"""Tests for LLM module."""

import pytest

from src.llm.json_extractor import extract_json, extract_json_with_fallback
from src.llm.prompt_manager import load_prompt, format_prompt, get_prompts_dir


def test_extract_json_simple():
    """Extract JSON from plain JSON string."""
    text = '{"procedure": "brain MRI", "payer": "Blue Cross"}'
    result = extract_json(text)
    assert result == {"procedure": "brain MRI", "payer": "Blue Cross"}


def test_extract_json_with_prose():
    """Extract JSON from response with surrounding text."""
    text = 'Here is the result:\n\n{"code": "70553", "confidence": "high"}\n\nHope this helps!'
    result = extract_json(text)
    assert result == {"code": "70553", "confidence": "high"}


def test_extract_json_no_json_returns_none():
    """No JSON in text returns None."""
    assert extract_json("No JSON here") is None


def test_extract_json_with_fallback():
    """Fallback returns dict with raw text when no JSON."""
    result = extract_json_with_fallback("No JSON")
    assert result == {"raw": "No JSON"}


def test_load_prompt():
    """Prompts load from config."""
    prompt = load_prompt("input_parser")
    assert "{query}" in prompt
    assert "procedure" in prompt


def test_format_prompt():
    """Prompt formatting works."""
    result = format_prompt("input_parser", query="brain MRI, Blue Cross")
    assert "brain MRI, Blue Cross" in result
    assert "{query}" not in result


def test_get_prompts_dir():
    """Prompts dir path exists."""
    path = get_prompts_dir()
    assert path.exists()
    assert "prompts" in str(path)
