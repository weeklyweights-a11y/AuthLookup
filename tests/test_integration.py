"""Integration tests."""

import pytest

from src.lookup.cpt_lookup import CPTLookup
from src.lookup.policy_lookup import PolicyLookup
from src.fhir.crd_generator import generate_crd_response
from src.fhir.dtr_generator import generate_dtr_questionnaire


def test_integration_cpt_to_fhir_no_ollama():
    """CPT lookup to FHIR output without Ollama."""
    cpt = CPTLookup()
    r = cpt.find_code("brain MRI with contrast")
    assert r["code"]

    policy = PolicyLookup()
    req = policy.get_requirements(r["code"], "Medicare")
    crd = generate_crd_response(r["code"], req)
    dtr = generate_dtr_questionnaire(r["code"], req)

    assert crd["resourceType"] == "CoverageEligibilityResponse"
    assert dtr["resourceType"] == "Questionnaire"
    assert crd["item"][0]["productOrService"]["coding"][0]["code"] == r["code"]
    assert req["source_section"].startswith("CMS MCD")
