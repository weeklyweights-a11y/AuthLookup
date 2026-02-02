"""Tests for config loader."""

from pathlib import Path

import pytest

from src.config.loader import load_config, get_config


def test_load_config():
    """Config loads from default path."""
    config = load_config()
    assert "paths" in config
    assert "ollama" in config
    assert "model" in config["ollama"]


def test_get_config_returns_dict():
    """get_config returns a dict."""
    cfg = get_config()
    assert isinstance(cfg, dict)
