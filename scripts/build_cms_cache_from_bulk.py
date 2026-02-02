"""
Build articles_cache.json from CMS bulk CSV (current_article + current_lcd).

Reads data/cms/current_article/csv/ and data/cms/current_lcd/csv/,
maps CPT -> article or LCD -> requirements, writes data/cms/articles_cache.json.
Cache includes codes from BOTH articles and LCDs; article data takes precedence
when a code appears in both.
"""

import csv
import json
import re
import sys
from pathlib import Path

csv.field_size_limit(2**24)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import get_config


def _strip_html(text: str, max_len: int = 800) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&\w+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len] if max_len else text


def _paragraph_to_bullets(paragraph: str, max_items: int = 8, max_len: int = 200) -> list[str]:
    """Turn a paragraph into short bullet-like items."""
    s = _strip_html(paragraph, max_len=2000)
    if not s:
        return []
    items = []
    for part in re.split(r"[.;]\s+", s):
        part = part.strip()
        if len(part) > 20:
            items.append(part[:max_len])
    return items[:max_items]


# Used only when source text yields no documentation or denial criteria
DOC_FALLBACK = ["See policy for documentation requirements"]
DENIAL_FALLBACK = ["See policy for denial criteria"]


def _parse_lcd_html_to_bullets(html: str, section_hint: str, max_items: int = 8, max_len: int = 200) -> list[str]:
    """Parse LCD HTML into short bullet items. Extracts <li>, <p>, and paragraph-like content."""
    if not html or not html.strip():
        return []
    text = html
    items: list[str] = []
    # Extract <li>...</li> content
    for m in re.finditer(r"<li[^>]*>([^<]+)", text, re.IGNORECASE | re.DOTALL):
        s = _strip_html(m.group(1), max_len + 50)
        if len(s) > 15:
            items.append(s[:max_len])
    # Extract content after section headings (Covered Indications, Documentation, Noncovered)
    section_keywords = {
        "doc": ["documentation", "documents required", "required documentation"],
        "criteria": ["covered indications", "covered", "medical necessity", "indications"],
        "denial": ["noncovered", "not covered", "denial", "does not support"],
    }
    keywords = section_keywords.get(section_hint, [])
    # Also split on <p> and get paragraphs
    for m in re.finditer(r"<p[^>]*>([^<]*(?:<[^/][^>]*>[^<]*)*)</p>", text, re.IGNORECASE | re.DOTALL):
        s = _strip_html(m.group(1), max_len + 50)
        if len(s) > 20 and not any(k in s.lower()[:30] for k in ["this lcd", "this policy", "note:"]):
            items.append(s[:max_len])
    # If we have few items, fall back to sentence splitting
    if len(items) < 3:
        s = _strip_html(text, 3000)
        for part in re.split(r"[.;]\s+", s):
            part = part.strip()
            if len(part) > 25 and len(part) < 500:
                items.append(part[:max_len])
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        xnorm = x.lower()[:80]
        if xnorm not in seen and len(out) < max_items:
            seen.add(xnorm)
            out.append(x)
    return out[:max_items]


def main() -> int:
    config = get_config()
    base = Path(__file__).resolve().parent.parent
    cms_cache_path = config.get("cms_api", {}).get("cache_path", "data/cms/articles_cache.json")
    cache_path = base / cms_cache_path if not Path(cms_cache_path).is_absolute() else Path(cms_cache_path)
    article_csv_dir = cache_path.parent / "current_article" / "csv"
    lcd_csv_dir = cache_path.parent / "current_lcd" / "csv"
    if not article_csv_dir.exists():
        print(f"Article CSV directory not found: {article_csv_dir}")
        print("Unzip current_article.zip and current_article_csv.zip into data/cms/current_article/")
        return 1
    if not lcd_csv_dir.exists():
        print(f"LCD CSV directory not found: {lcd_csv_dir}")
        print("Unzip current_lcd.zip and current_lcd_csv.zip into data/cms/current_lcd/")
        return 1

    def _open_csv(p: Path):
        return open(p, encoding="utf-8", errors="replace", newline="")

    # --- Articles: CPT -> (article_id, article_version) ---
    cpt_to_articles: dict[str, list[tuple[str, int]]] = {}
    with _open_csv(article_csv_dir / "article_x_hcpc_code.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            hcpc = (row.get("hcpc_code_id") or "").strip()
            if not hcpc or len(hcpc) < 4:
                continue
            aid = (row.get("article_id") or "").strip()
            try:
                ver = int((row.get("article_version") or "0").strip())
            except ValueError:
                ver = 0
            if aid:
                cpt_to_articles.setdefault(hcpc, []).append((aid, ver))

    # Dedupe: for each CPT pick one article (highest version)
    cpt_to_article: dict[str, tuple[str, int]] = {}
    for cpt, pairs in cpt_to_articles.items():
        best = max(pairs, key=lambda p: (p[1], p[0]))
        cpt_to_article[cpt] = best

    # Load article title/description
    articles: dict[tuple[str, int], dict] = {}
    with _open_csv(article_csv_dir / "article.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            aid = (row.get("article_id") or "").strip()
            try:
                ver = int((row.get("article_version") or "0").strip())
            except ValueError:
                ver = 0
            if not aid:
                continue
            title = (row.get("title") or "").strip()
            desc = (row.get("description") or "").strip()
            articles[(aid, ver)] = {"title": title, "description": desc}

    # Covered (medical necessity) paragraphs
    covered: dict[tuple[str, int], str] = {}
    with _open_csv(article_csv_dir / "article_x_icd10_covered_group.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            aid = (row.get("article_id") or "").strip()
            try:
                ver = int((row.get("article_version") or "0").strip())
            except ValueError:
                ver = 0
            para = (row.get("paragraph") or "").strip()
            if aid and para:
                covered[(aid, ver)] = covered.get((aid, ver), "") + " " + para

    # Noncovered (denial) paragraphs
    noncovered: dict[tuple[str, int], str] = {}
    with _open_csv(article_csv_dir / "article_x_icd10_noncovered_group.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            aid = (row.get("article_id") or "").strip()
            try:
                ver = int((row.get("article_version") or "0").strip())
            except ValueError:
                ver = 0
            para = (row.get("paragraph") or "").strip()
            if aid and para:
                noncovered[(aid, ver)] = noncovered.get((aid, ver), "") + " " + para

    # --- LCDs: CPT -> (lcd_id, lcd_version) ---
    cpt_to_lcds: dict[str, list[tuple[str, int]]] = {}
    with _open_csv(lcd_csv_dir / "lcd_x_hcpc_code.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            hcpc = (row.get("hcpc_code_id") or "").strip()
            if not hcpc or len(hcpc) < 4:
                continue
            lid = (row.get("lcd_id") or "").strip()
            try:
                ver = int((row.get("lcd_version") or "0").strip())
            except ValueError:
                ver = 0
            if lid:
                cpt_to_lcds.setdefault(hcpc, []).append((lid, ver))

    cpt_to_lcd: dict[str, tuple[str, int]] = {}
    for cpt, pairs in cpt_to_lcds.items():
        best = max(pairs, key=lambda p: (p[1], p[0]))
        cpt_to_lcd[cpt] = best

    # Load LCD title and criteria text (indication, doc_reqs, diagnoses_dont_support)
    lcds: dict[tuple[str, int], dict] = {}
    with _open_csv(lcd_csv_dir / "lcd.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lid = (row.get("lcd_id") or "").strip()
            try:
                ver = int((row.get("lcd_version") or "0").strip())
            except ValueError:
                ver = 0
            if not lid:
                continue
            title = (row.get("title") or "").strip()
            display_id = (row.get("display_id") or "").strip()
            indication = (row.get("indication") or "").strip()
            doc_reqs = (row.get("doc_reqs") or "").strip()
            diagnoses_dont_support = (row.get("diagnoses_dont_support") or "").strip()
            lcds[(lid, ver)] = {
                "title": title,
                "display_id": display_id or lid,
                "indication": indication,
                "doc_reqs": doc_reqs,
                "diagnoses_dont_support": diagnoses_dont_support,
            }

    # Build cache: all CPTs from articles and LCDs; article takes precedence when both exist
    all_cpts = set(cpt_to_article) | set(cpt_to_lcd)
    cache: dict[str, dict] = {}
    for cpt in all_cpts:
        if cpt in cpt_to_article:
            aid, ver = cpt_to_article[cpt]
            art = articles.get((aid, ver), {})
            title = art.get("title", "")
            desc = art.get("description", "")
            cov_text = covered.get((aid, ver), "")
            noncov_text = noncovered.get((aid, ver), "")

            # Derive from article description + covered text; no hardcoded doc list
            doc_required = _paragraph_to_bullets(desc + " " + cov_text, max_items=8, max_len=200)
            if not doc_required:
                doc_required = DOC_FALLBACK.copy()

            med_criteria = _paragraph_to_bullets(cov_text, max_items=6, max_len=250)
            if not med_criteria and cov_text:
                med_criteria = [_strip_html(cov_text, 400)]

            denial_reasons = _paragraph_to_bullets(noncov_text, max_items=5, max_len=200)
            if not denial_reasons and noncov_text:
                denial_reasons = [_strip_html(noncov_text, 300)]
            if not denial_reasons:
                denial_reasons = DENIAL_FALLBACK.copy()

            cache[cpt] = {
                "prior_auth_required": True,
                "documentation_required": doc_required,
                "medical_necessity_criteria": med_criteria or ["See LCD/article for criteria"],
                "common_denial_reasons": denial_reasons,
                "source_section": f"CMS MCD {title[:40]}" if title else "CMS MCD",
            }
        else:
            lid, ver = cpt_to_lcd[cpt]
            lcd = lcds.get((lid, ver), {})
            title = lcd.get("title", "")
            display_id = lcd.get("display_id", lid)
            indication = lcd.get("indication", "")
            doc_reqs = lcd.get("doc_reqs", "")
            noncov_text = lcd.get("diagnoses_dont_support", "")

            # Parse LCD columns with improved HTML-to-bullets
            doc_required = _parse_lcd_html_to_bullets(doc_reqs, "doc", max_items=8, max_len=200)
            if not doc_required and indication:
                doc_required = _parse_lcd_html_to_bullets(indication, "doc", max_items=6, max_len=200)
            if not doc_required:
                doc_required = DOC_FALLBACK.copy()

            med_criteria = _parse_lcd_html_to_bullets(indication, "criteria", max_items=6, max_len=250)
            if not med_criteria and indication:
                med_criteria = _paragraph_to_bullets(indication, max_items=6, max_len=250)
            if not med_criteria and indication:
                med_criteria = [_strip_html(indication, 400)]

            denial_reasons = _parse_lcd_html_to_bullets(noncov_text, "denial", max_items=5, max_len=200)
            if not denial_reasons and noncov_text:
                denial_reasons = _paragraph_to_bullets(noncov_text, max_items=5, max_len=200)
            if not denial_reasons and noncov_text:
                denial_reasons = [_strip_html(noncov_text, 300)]
            if not denial_reasons:
                denial_reasons = DENIAL_FALLBACK.copy()

            cache[cpt] = {
                "prior_auth_required": True,
                "documentation_required": doc_required,
                "medical_necessity_criteria": med_criteria or ["See LCD for criteria"],
                "common_denial_reasons": denial_reasons,
                "source_section": f"CMS LCD L{display_id}",
            }

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)
    article_only = len(cpt_to_article)
    lcd_only = len(cpt_to_lcd)
    overlap = len(set(cpt_to_article) & set(cpt_to_lcd))
    print(f"Articles: {article_only} CPTs | LCDs: {lcd_only} CPTs | Overlap: {overlap}")
    print(f"Wrote {len(cache)} CPT entries to {cache_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
