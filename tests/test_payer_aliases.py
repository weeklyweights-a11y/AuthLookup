"""Tests for payer aliases."""

from src.lookup.payer_aliases import normalize_payer


def test_normalize_medicare():
    """Medicare aliases normalize correctly."""
    assert normalize_payer("medicare") == "Medicare"
    assert normalize_payer("cms") == "Medicare"
    assert normalize_payer("MAC") == "Medicare"


def test_normalize_uhc():
    """UnitedHealthcare aliases normalize correctly."""
    assert normalize_payer("uhc") == "UnitedHealthcare"
    assert normalize_payer("united") == "UnitedHealthcare"
    assert normalize_payer("UnitedHealthcare") == "UnitedHealthcare"


def test_normalize_anthem():
    """Anthem aliases normalize correctly."""
    assert normalize_payer("anthem") == "Anthem"
    assert normalize_payer("blue_cross") == "Anthem"


def test_unknown_passes_through():
    """Unknown payer passes through as-is."""
    result = normalize_payer("SomeOtherPayer")
    assert result == "SomeOtherPayer"
