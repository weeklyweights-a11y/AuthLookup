"""Configuration loader with environment variable overrides."""

import os
from pathlib import Path
from typing import Any

import yaml


_config: dict[str, Any] | None = None


def load_config(config_path: str | None = None) -> dict[str, Any]:
    """Load configuration from YAML file with environment variable overrides."""
    global _config
    if _config is not None:
        return _config

    if config_path is None:
        base_dir = Path(__file__).resolve().parent.parent.parent
        config_path = base_dir / "config" / "default.yaml"

    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        _config = yaml.safe_load(f) or {}

    # Resolve paths relative to project root
    project_root = config_path.parent.parent
    if "paths" in _config:
        for key, value in _config["paths"].items():
            if isinstance(value, str) and not Path(value).is_absolute():
                _config["paths"][key] = str(project_root / value)

    # Environment overrides
    _config["ollama"] = _config.get("ollama", {})
    if os.getenv("AUTHLOOKUP_OLLAMA_MODEL"):
        _config["ollama"]["model"] = os.getenv("AUTHLOOKUP_OLLAMA_MODEL")
    if os.getenv("AUTHLOOKUP_OLLAMA_BASE_URL"):
        _config["ollama"]["base_url"] = os.getenv("AUTHLOOKUP_OLLAMA_BASE_URL")

    return _config


def get_config() -> dict[str, Any]:
    """Get loaded configuration. Loads if not already loaded."""
    if _config is None:
        load_config()
    return _config or {}
