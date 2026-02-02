"""
Build cpt_codes.json from CMS bulk CSV (article_x_hcpc_code + lcd_x_hcpc_code).

Reads data/cms/current_article/csv/article_x_hcpc_code.csv and
data/cms/current_lcd/csv/lcd_x_hcpc_code.csv, dedupes by hcpc_code_id,
builds keywords from long_description + short_description with body-part
synonym expansion so procedure phrases (e.g. "MRI of the knee") map to
the correct CPT code (73721, not 70540).
"""

import csv
import json
import re
import sys
from pathlib import Path

csv.field_size_limit(2**24)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import get_config


# Body-part synonym expansion: add these keywords when description contains trigger phrases.
# So "MRI of the knee" matches 73721 (lower extremity joint) via knee/joint/lwr/extre.
BODY_PART_SYNONYMS: list[tuple[list[str], list[str]]] = [
    # (trigger substrings in description, keywords to add)
    (["lower extremity", "lwr extre", "joint of lower", "any joint"], ["knee", "joint", "lower", "extremity", "lwr", "extre"]),
    (["orbit", "face", "neck", "head and neck", "cranial"], ["brain", "head", "cranial", "orbit", "face", "neck"]),
    (["spine", "cervical", "thoracic", "lumbar", "spinal"], ["spine", "cervical", "thoracic", "lumbar"]),
]


def _tokenize(text: str, min_len: int = 3, max_keywords: int = 25) -> list[str]:
    """Lowercase, split on non-alphanumeric, keep tokens with len >= min_len."""
    if not text:
        return []
    s = re.sub(r"[^a-z0-9\s]", " ", text.lower()).strip()
    tokens = [w for w in s.split() if len(w) >= min_len]
    seen: set[str] = set()
    out: list[str] = []
    for w in tokens:
        if w not in seen and len(out) < max_keywords:
            seen.add(w)
            out.append(w)
    return out


def _add_body_part_keywords(description: str, short: str, keywords: list[str]) -> list[str]:
    """Add body-part synonym keywords when description matches trigger phrases."""
    combined = (description or "") + " " + (short or "")
    combined_lower = combined.lower()
    result = list(keywords)
    added: set[str] = set(keywords)
    for triggers, synonyms in BODY_PART_SYNONYMS:
        if any(t in combined_lower for t in triggers):
            for s in synonyms:
                if s not in added:
                    result.append(s)
                    added.add(s)
    return result


def main() -> int:
    config = get_config()
    base = Path(__file__).resolve().parent.parent
    cms_cache_path = config.get("cms_api", {}).get("cache_path", "data/cms/articles_cache.json")
    cache_path = base / cms_cache_path if not Path(cms_cache_path).is_absolute() else Path(cms_cache_path)
    article_csv_dir = cache_path.parent / "current_article" / "csv"
    lcd_csv_dir = cache_path.parent / "current_lcd" / "csv"
    output_path = base / "data" / "cpt" / "cpt_codes.json"

    if not article_csv_dir.exists():
        print(f"Article CSV directory not found: {article_csv_dir}")
        return 1
    if not lcd_csv_dir.exists():
        print(f"LCD CSV directory not found: {lcd_csv_dir}")
        return 1

    def _open_csv(p: Path):
        return open(p, encoding="utf-8", errors="replace", newline="")

    # Collect all rows: (last_updated, long_description, short_description).
    # Prefer article over LCD for same code; then prefer latest last_updated within same source.
    rows_by_code: dict[str, tuple[str, str, str]] = {}

    def ingest(path: Path) -> None:
        if not path.exists():
            return
        with _open_csv(path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = (row.get("hcpc_code_id") or "").strip()
                if not code or len(code) < 2:
                    continue
                long_d = (row.get("long_description") or "").strip()
                short_d = (row.get("short_description") or "").strip()
                updated = (row.get("last_updated") or "").strip()
                if code not in rows_by_code or updated > rows_by_code[code][0]:
                    rows_by_code[code] = (updated, long_d or short_d, short_d)

    ingest(article_csv_dir / "article_x_hcpc_code.csv")
    # LCD: only add codes not already present (article takes precedence)
    if lcd_csv_dir.exists():
        with _open_csv(lcd_csv_dir / "lcd_x_hcpc_code.csv") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = (row.get("hcpc_code_id") or "").strip()
                if not code or len(code) < 2 or code in rows_by_code:
                    continue
                long_d = (row.get("long_description") or "").strip()
                short_d = (row.get("short_description") or "").strip()
                updated = (row.get("last_updated") or "").strip()
                rows_by_code[code] = (updated, long_d or short_d, short_d)

    cpt_codes: dict[str, dict] = {}
    for code, (_, long_desc, short_desc) in rows_by_code.items():
        description = long_desc or short_desc
        if not description:
            continue
        keywords = _tokenize(description + " " + short_desc)
        keywords = _add_body_part_keywords(long_desc, short_desc, keywords)
        # Modality synonyms so "mri" in query matches "MAGNETIC RESONANCE IMAGING" descriptions
        desc_lower = (long_desc + " " + short_desc).lower()
        if "magnetic resonance" in desc_lower or "mri" in desc_lower:
            if "mri" not in keywords:
                keywords.append("mri")
        if "computerized tomography" in desc_lower or " ct " in desc_lower or "ct scan" in desc_lower:
            if "ct" not in keywords:
                keywords.append("ct")
        if code not in keywords:
            keywords.append(code)
        cpt_codes[code] = {
            "description": description,
            "short_description": short_desc,
            "category": "imaging" if any(k in description.lower() for k in ("mri", "ct", "x-ray", "ultrasound", "imaging")) else "general",
            "keywords": keywords[:30],
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cpt_codes, f, indent=2)
    print(f"Wrote {len(cpt_codes)} CPT entries to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
