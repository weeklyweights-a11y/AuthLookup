"""Generate FHIR Questionnaire (DTR)."""

from typing import Any

from src.fhir.fhir_utils import generate_id


def generate_dtr_questionnaire(cpt_code: str, requirements: dict[str, Any]) -> dict[str, Any]:
    """Generate FHIR Questionnaire for DTR from PA requirements."""
    items = []
    link_id = 1

    for doc in requirements.get("documentation_required", []):
        items.append({
            "linkId": str(link_id),
            "text": f"Provide: {doc}",
            "type": "string",
            "required": True,
        })
        link_id += 1

    for criteria in requirements.get("medical_necessity_criteria", []):
        items.append({
            "linkId": str(link_id),
            "text": criteria,
            "type": "boolean",
            "required": True,
        })
        link_id += 1

    return {
        "resourceType": "Questionnaire",
        "id": generate_id("dtr"),
        "status": "active",
        "title": f"Prior Authorization - CPT {cpt_code}",
        "subjectType": ["Patient"],
        "item": items,
    }
