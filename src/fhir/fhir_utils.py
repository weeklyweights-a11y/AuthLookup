"""Shared FHIR utilities."""
from datetime import datetime
import uuid


def generate_id(prefix: str = "authlookup") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def fhir_datetime() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00")


def cpt_coding(code: str) -> dict:
    return {"system": "http://www.ama-assn.org/go/cpt", "code": code}
