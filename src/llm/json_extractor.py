"""Extract and validate JSON from LLM responses."""

import json
import re
from typing import Any


def extract_json(text: str) -> dict[str, Any] | None:
    """
    Extract first JSON object from text.

    Handles LLM responses that may include prose around the JSON.
    """
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def extract_json_with_fallback(text: str) -> dict[str, Any]:
    """Extract JSON or return fallback with raw text."""
    result = extract_json(text)
    if result is not None:
        return result
    return {"raw": text}
