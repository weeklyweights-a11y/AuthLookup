"""Tests for Ollama client (mocked)."""

from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("ollama")


@patch("src.llm.ollama_client.ollama")
def test_ollama_client_query_mock(mock_ollama):
    """Ollama client sends query and returns response."""
    mock_client = MagicMock()
    mock_client.chat.return_value = {"message": {"content": "Hello"}}
    mock_ollama.Client.return_value = mock_client

    from src.llm.ollama_client import OllamaClient

    client = OllamaClient()
    result = client.query("test prompt")
    assert result == "Hello"
    mock_client.chat.assert_called_once()


@patch("src.llm.ollama_client.ollama")
def test_ollama_client_extract_json_mock(mock_ollama):
    """extract_json parses JSON from response."""
    mock_client = MagicMock()
    mock_client.chat.return_value = {
        "message": {"content": '{"code": "70553", "confidence": "high"}'}
    }
    mock_ollama.Client.return_value = mock_client

    from src.llm.ollama_client import OllamaClient

    client = OllamaClient()
    result = client.extract_json("map to CPT")
    assert result["code"] == "70553"
    assert result["confidence"] == "high"
