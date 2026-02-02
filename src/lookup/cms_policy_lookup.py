"""CMS Medicare Coverage Database policy lookup via cached API data."""

import json
from pathlib import Path
from typing import Any

from src.config import get_config


class CMSPolicyLookup:
    """Look up Medicare coverage requirements from CMS MCD cache."""

    def __init__(self, cache_path: str | Path | None = None) -> None:
        config = get_config()
        cms_config = config.get("cms_api", {})
        paths = config.get("paths", {})
        base = Path(__file__).resolve().parent.parent.parent

        path = cache_path or cms_config.get("cache_path", "data/cms/articles_cache.json")
        path = Path(path)
        if not path.is_absolute():
            path = base / path
        self.cache_path = path
        self._cache: dict[str, Any] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Load cache from JSON file."""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, encoding="utf-8") as f:
                    self._cache = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._cache = {}
        else:
            self._cache = {}

    def get_requirements(self, cpt_code: str) -> dict[str, Any] | None:
        """
        Get PA requirements for CPT code from CMS cache.

        Returns requirements dict if found, None otherwise.
        """
        cpt_clean = str(cpt_code).strip()
        if cpt_clean not in self._cache:
            return None
        entry = self._cache[cpt_clean]
        if isinstance(entry, dict) and "prior_auth_required" in entry:
            return entry
        return self._map_entry_to_requirements(cpt_clean, entry)

    def _map_entry_to_requirements(self, cpt_code: str, entry: Any) -> dict[str, Any]:
        """Map cache entry to requirements schema."""
        if isinstance(entry, dict):
            return {
                "prior_auth_required": entry.get("prior_auth_required", True),
                "documentation_required": entry.get("documentation_required", []),
                "medical_necessity_criteria": entry.get("medical_necessity_criteria", []),
                "common_denial_reasons": entry.get("common_denial_reasons", []),
                "source_section": entry.get("source_section", "CMS MCD"),
            }
        return {
            "prior_auth_required": True,
            "documentation_required": ["See CMS MCD for details"],
            "medical_necessity_criteria": [],
            "common_denial_reasons": ["Criteria not met"],
            "source_section": "CMS MCD",
        }
