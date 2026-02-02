"""Generate FHIR CoverageEligibilityResponse (CRD)."""

from typing import Any

from src.fhir.fhir_utils import generate_id, fhir_datetime, cpt_coding


def generate_crd_response(cpt_code: str, requirements: dict[str, Any]) -> dict[str, Any]:
    """Generate FHIR CoverageEligibilityResponse for prior auth requirements."""
    docs = requirements.get("documentation_required", [])
    auth_supporting = [{"coding": [{"display": d}]} for d in docs] if docs else []

    return {
        "resourceType": "CoverageEligibilityResponse",
        "id": generate_id("crd"),
        "status": "active",
        "purpose": ["auth-requirements"],
        "created": fhir_datetime(),
        "item": [
            {
                "productOrService": {"coding": [cpt_coding(cpt_code)]},
                "authorizationRequired": requirements.get("prior_auth_required", True),
                "authorizationSupporting": auth_supporting,
            }
        ],
    }
