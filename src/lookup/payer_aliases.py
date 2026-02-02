"""Payer name normalization via config-driven aliases."""

from src.config import get_config


def normalize_payer(payer_input: str) -> str:
    """
    Map user input to canonical payer name via config payer_aliases.

    Returns canonical name if found, otherwise passes through input as-is.
    """
    if not payer_input or not isinstance(payer_input, str):
        return payer_input or "Unknown"
    raw = payer_input.strip()
    key = raw.lower().replace(" ", "_")
    key_alt = raw.lower()
    config = get_config()
    aliases = config.get("payer_aliases", {})
    for k in (key, key_alt, key.replace("_", "")):
        if k in aliases:
            return aliases[k]
    return raw or "Unknown"
