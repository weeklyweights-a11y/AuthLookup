"""Tests for policy lookup."""

from src.lookup.policy_lookup import PolicyLookup, _default_requirements


def test_default_requirements():
    """Default requirements have expected keys."""
    r = _default_requirements()
    assert "prior_auth_required" in r
    assert "documentation_required" in r
    assert "medical_necessity_criteria" in r
    assert r["source_section"] == "default"


def test_policy_lookup_returns_cms_for_medicare():
    """PolicyLookup returns CMS data for Medicare (config-driven)."""
    pl = PolicyLookup()
    r = pl.get_requirements("70553", "Medicare")
    assert r["source_section"].startswith("CMS MCD")
    assert "documentation_required" in r


def test_policy_lookup_returns_default_when_no_data():
    """PolicyLookup returns default when payer not in config."""
    pl = PolicyLookup()
    r = pl.get_requirements("70553", "UnknownPayerXYZ")
    assert "prior_auth_required" in r
    assert isinstance(r["documentation_required"], list)
    assert r["source_section"] == "default"
