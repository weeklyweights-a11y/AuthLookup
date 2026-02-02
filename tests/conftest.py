"""Pytest fixtures for AuthLookup tests."""

import pytest


@pytest.fixture
def sample_config():
    """Sample config for testing."""
    return {
        "paths": {"cpt_file": "data/cpt/cpt_codes.json"},
        "ollama": {"model": "llama3:8b", "timeout": 60},
    }
