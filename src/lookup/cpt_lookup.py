"""CPT code lookup."""

import json
from pathlib import Path
from typing import Any

from src.config import get_config


# Body-part alignment: procedure terms -> description/keyword terms that indicate a match.
# E.g. "knee" in query should strongly prefer codes with "lower extremity" / "joint".
BODY_PART_ALIGNMENT: dict[str, list[str]] = {
    "knee": ["knee", "joint", "lower", "extremity", "lwr", "extre"],
    "brain": ["brain", "head", "cranial"],
    "head": ["brain", "head", "cranial", "orbit", "face", "neck"],
    "neck": ["neck", "orbit", "face", "head"],
    "spine": ["spine", "cervical", "thoracic", "lumbar", "spinal"],
    "cervical": ["cervical", "spine", "neck"],
    "thoracic": ["thoracic", "spine"],
    "lumbar": ["lumbar", "spine"],
}


class CPTLookup:
    """Map procedure description to CPT code."""

    def __init__(self, cpt_file: str | Path | None = None, cms_cache_path: str | Path | None = None) -> None:
        config = get_config()
        base = Path(__file__).resolve().parent.parent.parent
        path = cpt_file or config.get("paths", {}).get("cpt_file", "data/cpt/cpt_codes.json")
        path = Path(path)
        if not path.is_absolute():
            path = base / path
        with open(path, encoding="utf-8") as f:
            self.cpt_codes = json.load(f)
        self._index: dict[str, list[tuple[str, dict]]] = {}
        for code, info in self.cpt_codes.items():
            for kw in info.get("keywords", []) + [info.get("description", "").lower()]:
                kw = kw.lower().strip()
                if len(kw) > 2:
                    self._index.setdefault(kw, []).append((code, info))
        # Restrict to codes present in CMS cache so we only return codes we have policy for.
        self._cms_cache_codes: set[str] = set()
        cache_path = cms_cache_path or config.get("cms_api", {}).get("cache_path", "data/cms/articles_cache.json")
        cache_path = Path(cache_path)
        if not cache_path.is_absolute():
            cache_path = base / cache_path
        if cache_path.exists():
            try:
                with open(cache_path, encoding="utf-8") as f:
                    cache = json.load(f)
                self._cms_cache_codes = set(cache.keys())
            except (json.JSONDecodeError, OSError):
                pass

    def _allowed_codes(self) -> set[str]:
        """Codes we are allowed to return (CMS cache keys); if empty, allow all."""
        if not self._cms_cache_codes:
            return set(self.cpt_codes.keys())
        return self._cms_cache_codes & set(self.cpt_codes.keys())

    def find_code(self, procedure: str) -> dict[str, Any]:
        """Find CPT code by keyword matching with body-part alignment."""
        proc = procedure.lower()
        allowed = self._allowed_codes()
        scores: dict[str, float] = {}
        for word in proc.split():
            word = word.strip(".,;")
            if len(word) < 3:
                continue
            for code, info in self._index.get(word, []):
                if allowed and code not in allowed:
                    continue
                desc = info.get("description", "").lower()
                keywords_str = " ".join(info.get("keywords", [])).lower()
                combined = desc + " " + keywords_str
                s = 1.0
                if word in desc:
                    s += 0.5
                if "mri" in proc and ("mri" in desc or ("magnetic" in combined and "resonance" in combined)):
                    s += 2.0
                    # Prefer primary MRI imaging over injection/arthrography when procedure is "MRI of X"
                    if (desc.startswith("magnetic resonance") or desc.startswith("mri ")) and "injection" not in desc[:50]:
                        s += 1.5
                if "contrast" in proc and ("contrast" in desc or "dye" in combined):
                    s += 1.5
                    # Prefer "without then with" (70553) over "with only" (70552) when user wants contrast
                    if "without contrast" not in proc and ("brain" in proc or "head" in proc):
                        if "followed by" in desc and "without" in desc:
                            s += 2.0  # Boost full protocol (without then with)
                        elif "with contrast" in desc or "with contrast" in combined:
                            if "followed by" not in desc:
                                s -= 1.5  # Penalize "with only" when full protocol exists
                # Body-part alignment: procedure mentions knee/brain/head/neck/spine -> boost matching codes
                for proc_term, desc_terms in BODY_PART_ALIGNMENT.items():
                    if proc_term in proc and any(d in combined for d in desc_terms):
                        s += 2.0
                        # Prefer "joint of lower extremity" (73721) over upper-extremity or "other than joint" for knee
                        if proc_term == "knee" and "joint" in combined and "other than joint" not in desc and "lower" in combined:
                            s += 1.0
                        break
                # Penalize intraoperative codes (70557, 70558) when query is routine brain MRI
                proc_is_routine = not any(
                    x in proc for x in ["intraoperative", "during surgery", "open procedure", "during open"]
                )
                desc_is_intraop = "during open intracranial" in desc or "intraoperative" in desc
                if proc_is_routine and desc_is_intraop:
                    s -= 5.0
                scores[code] = scores.get(code, 0) + s
        if scores:
            def _tie_key(c: str) -> tuple:
                desc = (self.cpt_codes[c].get("description") or "").lower()
                # For "knee", prefer lower extremity (73721) over upper (73223)
                knee_lower = 1 if ("knee" in proc and "lower" in desc and "upper" not in desc) else 0
                # When contrast not specified, prefer "without contrast" only (73721) over "without then with" (73723)
                simple_mri = 1 if ("with contrast" not in proc and "followed by" not in desc and "without" in desc) else 0
                # When "with contrast" in query, prefer "without then with" (70553) over "with only" (70552) - full protocol
                with_and_without = 1 if ("with contrast" in proc and "followed by" in desc and "contrast" in desc) else 0
                # Prefer routine brain MRI (70551, 70553) over intraoperative (70557, 70558)
                routine_brain = 1 if (("brain" in proc or "head" in proc) and "during open" not in desc) else 0
                return (scores[c], routine_brain, with_and_without, knee_lower, simple_mri, len(desc))
            best = max(scores, key=_tie_key)
            return {"code": best, "description": self.cpt_codes[best].get("description", ""), "match": "keyword", "confidence": "high" if scores[best] >= 2 else "medium"}
        return {"code": "", "description": "", "match": "none", "confidence": "low"}

    def _cpt_list_for_llm(self, procedure: str, max_codes: int = 120) -> str:
        """Build CPT list for LLM: only allowed (CMS cache) codes, optionally filtered by modality."""
        allowed = self._allowed_codes()
        candidates = [(c, self.cpt_codes[c]) for c in self.cpt_codes if c in allowed]
        proc_lower = procedure.lower()
        # If procedure mentions a modality, prefer codes whose description matches it
        if "mri" in proc_lower:
            candidates = [(c, i) for c, i in candidates if "mri" in (i.get("description") or "").lower()]
        elif "ct" in proc_lower or "cat " in proc_lower:
            candidates = [(c, i) for c, i in candidates if "ct " in (i.get("description") or "").lower() or "tomography" in (i.get("description") or "").lower()]
        if not candidates:
            candidates = [(c, self.cpt_codes[c]) for c in self.cpt_codes if c in allowed]
        # Use full long description for better LLM matching
        lines = [f"{c}: {i.get('description', '')}" for c, i in candidates[:max_codes]]
        return "\n".join(lines)

    def find_code_with_llm(self, procedure: str, ollama_client: Any = None) -> dict[str, Any]:
        """LLM fallback when keyword match fails or confidence low; uses cpt_mapper prompt with filtered CMS codes."""
        r = self.find_code(procedure)
        if r["code"] and r["confidence"] in ("high", "medium"):
            return r
        if ollama_client is None:
            try:
                from src.llm.ollama_client import OllamaClient
                ollama_client = OllamaClient()
            except ImportError:
                return r
        try:
            from src.llm.prompt_manager import format_prompt
            cpt_list = self._cpt_list_for_llm(procedure)
            prompt = format_prompt("cpt_mapper", procedure=procedure, cpt_list=cpt_list)
        except FileNotFoundError:
            cpt_list = "\n".join(f"{c}: {i.get('description','')}" for c, i in list(self.cpt_codes.items())[:80])
            prompt = f'Map to CPT: "{procedure}"\n{cpt_list}\nJSON: {{"code":"XXX","description":"...","confidence":"high"}}'
        out = ollama_client.extract_json(prompt)
        allowed = self._allowed_codes()
        if out.get("code"):
            c = str(out["code"]).strip()
            if c in self.cpt_codes and (not allowed or c in allowed):
                return {"code": c, "description": self.cpt_codes[c].get("description", ""), "match": "llm", "confidence": out.get("confidence", "medium")}
        return r
