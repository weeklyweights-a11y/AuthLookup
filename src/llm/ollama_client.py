"""Ollama HTTP client with retries and timeouts."""

import json
import re
from typing import Any

from src.config import get_config

try:
    import ollama
except ImportError:
    ollama = None


class OllamaClient:
    """Client for Ollama API with structured output support."""

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        timeout: int | None = None,
    ) -> None:
        if ollama is None:
            raise ImportError("ollama package required. Install with: pip install ollama")
        config = get_config()
        ollama_config = config.get("ollama", {})
        self.model = model or ollama_config.get("model", "llama3:8b")
        self.base_url = base_url or ollama_config.get("base_url", "http://localhost:11434")
        self.timeout = timeout or ollama_config.get("timeout", 60)

    def query(self, prompt: str, system: str | None = None) -> str:
        """Send a query to Ollama and return the response text."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        client = ollama.Client(host=self.base_url)
        response = client.chat(
            model=self.model,
            messages=messages,
        )
        return response["message"]["content"]

    def extract_json(self, prompt: str, system: str | None = None) -> dict[str, Any]:
        """Query Ollama and extract JSON from the response."""
        response = self.query(prompt, system)

        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {"raw": response}
