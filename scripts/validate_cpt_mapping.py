"""
Validate procedure -> CPT mapping against a fixture.

Reads tests/fixtures/cpt_mapping.json (procedure, expected_cpt or expected_cpt_candidates),
runs CPTLookup().find_code(procedure) for each, exits 1 on first mismatch.
Skips (exit 0) when CMS cache or cpt_codes.json is missing so CI passes without CMS data.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.lookup.cpt_lookup import CPTLookup


def main() -> int:
    base = Path(__file__).resolve().parent.parent
    fixture_path = base / "tests" / "fixtures" / "cpt_mapping.json"
    cache_path = base / "data" / "cms" / "articles_cache.json"
    cpt_path = base / "data" / "cpt" / "cpt_codes.json"

    if not cpt_path.exists():
        print("Skipping CPT validation: data/cpt/cpt_codes.json not found (run build_cpt_from_cms.py)")
        return 0
    if not cache_path.exists():
        print("Skipping CPT validation: data/cms/articles_cache.json not found (run build_cms_cache_from_bulk.py)")
        return 0
    if not fixture_path.exists():
        print("Skipping CPT validation: tests/fixtures/cpt_mapping.json not found")
        return 0

    with open(fixture_path, encoding="utf-8") as f:
        fixtures = json.load(f)

    lookup = CPTLookup()
    for item in fixtures:
        procedure = item.get("procedure", "")
        expected = item.get("expected_cpt")
        candidates = item.get("expected_cpt_candidates")
        r = lookup.find_code(procedure)
        got = r.get("code", "")
        if expected is not None:
            if got != expected:
                print(f"FAIL: procedure={procedure!r} -> got {got!r}, expected {expected!r}")
                return 1
        elif candidates is not None:
            if got not in candidates:
                print(f"FAIL: procedure={procedure!r} -> got {got!r}, expected one of {candidates}")
                return 1
    print("CPT mapping validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
