"""
Fetch CPT codes and create imaging subset for AuthLookup.

Downloads from CPT Gist and creates data/cpt/cpt_codes.json with imaging codes.
"""

import json
import sys
from pathlib import Path

import requests

GIST_URL = "https://gist.githubusercontent.com/lieldulev/439793dc3c5a6613b661c33d71fdd185/raw"
IMAGING_KEYWORDS = [
    "mri", "ct ", "ct scan", "x-ray", "x ray", "ultrasound", "us ",
    "imaging", "radiolog", "neuro", "brain", "spine", "joint", "extremity",
    "contrast", "without contrast", "with contrast", "mammograph",
    "fluoroscopy", "angiography", "nuclear"
]


def is_imaging_code(code: str, label: str) -> bool:
    """Check if CPT code is imaging-related based on code range and label."""
    label_lower = label.lower()
    for kw in IMAGING_KEYWORDS:
        if kw in label_lower:
            return True
    # Radiology codes: 70000-79999
    try:
        num = int(code)
        if 70000 <= num <= 79999:
            return True
        if 76000 <= num <= 76999:  # Diagnostic ultrasound
            return True
    except ValueError:
        pass
    return False


def fetch_and_convert(output_path: Path) -> int:
    """Fetch CPT data and create imaging subset JSON."""
    print("Fetching CPT codes from Gist...")
    resp = requests.get(GIST_URL, timeout=30)
    resp.raise_for_status()

    cpt_codes = {}
    lines = resp.text.strip().split("\n")
    header = lines[0] if lines else ""

    for line in lines[1:]:
        parts = line.split(",", 1)
        if len(parts) < 2:
            continue
        code = parts[0].strip()
        label = parts[1].strip().strip('"')

        if not code or not code[0].isdigit():
            continue

        if is_imaging_code(code, label):
            keywords = [w for w in label.lower().split() if len(w) > 2]
            cpt_codes[code] = {
                "description": label,
                "category": "imaging",
                "keywords": keywords[:10] + [code],
            }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cpt_codes, f, indent=2)

    print(f"Wrote {len(cpt_codes)} imaging CPT codes to {output_path}")
    return len(cpt_codes)


def main() -> int:
    base_dir = Path(__file__).resolve().parent.parent
    output_path = base_dir / "data" / "cpt" / "cpt_codes.json"
    count = fetch_and_convert(output_path)
    return 0 if count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
