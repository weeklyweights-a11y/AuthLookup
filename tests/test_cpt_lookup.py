"""Tests for CPT lookup."""

from src.lookup.cpt_lookup import CPTLookup


def test_find_code_mri_knee():
    """MRI of the knee maps to 73721 (MRI any joint of lower extremity without contrast)."""
    lookup = CPTLookup()
    r = lookup.find_code("MRI of the knee")
    assert r["code"] == "73721", f"Expected 73721, got {r['code']}"
    assert "joint" in r["description"].lower() and "lower" in r["description"].lower()


def test_find_code_brain_mri_with_contrast():
    """Brain MRI with contrast maps to 70553 (without then with - full protocol)."""
    lookup = CPTLookup()
    r = lookup.find_code("brain MRI with contrast")
    assert r["code"] == "70553", f"Expected 70553, got {r['code']}"
    assert "followed by" in r["description"].lower() or "magnetic" in r["description"].lower()


def test_find_code_mri_head_neck_without_contrast():
    """MRI head/neck without contrast maps to 70540 (orbit/face/neck without contrast)."""
    lookup = CPTLookup()
    r = lookup.find_code("MRI head neck without contrast")
    assert r["code"] == "70540", f"Expected 70540, got {r['code']}"
    assert "orbit" in r["description"].lower() or "face" in r["description"].lower() or "neck" in r["description"].lower()


def test_find_code_brain_mri():
    """Brain MRI with contrast maps to 70553 or similar."""
    lookup = CPTLookup()
    r = lookup.find_code("brain MRI with contrast")
    assert r["code"]
    assert "mri" in r["description"].lower() or "7055" in r["code"]


def test_find_code_returns_dict():
    """find_code returns dict with code, description, match, confidence."""
    lookup = CPTLookup()
    r = lookup.find_code("CT scan head")
    assert "code" in r
    assert "description" in r
    assert "match" in r
    assert "confidence" in r
