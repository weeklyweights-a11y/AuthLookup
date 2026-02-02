"""Tests for FHIR generators."""
from src.fhir.crd_generator import generate_crd_response
from src.fhir.dtr_generator import generate_dtr_questionnaire


def test_crd_generator():
    """CRD response has correct structure."""
    req = {"prior_auth_required": True, "documentation_required": ["H&P", "Labs"]}
    crd = generate_crd_response("70553", req)
    assert crd["resourceType"] == "CoverageEligibilityResponse"
    assert crd["status"] == "active"
    assert len(crd["item"]) == 1
    assert crd["item"][0]["productOrService"]["coding"][0]["code"] == "70553"


def test_dtr_generator():
    """DTR questionnaire has items from requirements."""
    req = {"documentation_required": ["History"], "medical_necessity_criteria": ["Criteria 1"]}
    dtr = generate_dtr_questionnaire("70553", req)
    assert dtr["resourceType"] == "Questionnaire"
    assert "70553" in dtr["title"]
    assert len(dtr["item"]) >= 2
