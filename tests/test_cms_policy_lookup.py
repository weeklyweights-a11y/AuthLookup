"""Tests for CMS policy lookup."""

from unittest.mock import patch
import json
from pathlib import Path

import pytest

from src.lookup.cms_policy_lookup import CMSPolicyLookup


def test_cms_lookup_returns_requirements_when_cached():
    """CMSPolicyLookup returns requirements when CPT in cache."""
    lookup = CMSPolicyLookup()
    r = lookup.get_requirements("70553")
    assert r is not None
    assert "prior_auth_required" in r
    assert "documentation_required" in r
    assert "medical_necessity_criteria" in r
    assert r["source_section"].startswith("CMS MCD")


def test_cms_lookup_returns_none_when_not_cached():
    """CMSPolicyLookup returns None when CPT not in cache."""
    lookup = CMSPolicyLookup()
    r = lookup.get_requirements("99999")
    assert r is None


def test_cms_lookup_schema():
    """Requirements have expected schema."""
    lookup = CMSPolicyLookup()
    r = lookup.get_requirements("70551")
    assert r is not None
    assert isinstance(r["documentation_required"], list)
    assert isinstance(r["medical_necessity_criteria"], list)
    assert isinstance(r["common_denial_reasons"], list)
