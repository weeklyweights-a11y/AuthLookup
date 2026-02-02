"""Policy lookup - CPT + payer to PA requirements (config-driven)."""

import json
from pathlib import Path
from typing import Any

from src.config import get_config
from src.lookup.payer_aliases import normalize_payer


def _default_requirements() -> dict[str, Any]:
    """Default requirements when no policy data found. Uses generic fallbacks consistent with CMS cache builder."""
    return {
        "prior_auth_required": True,
        "documentation_required": ["See policy for documentation requirements"],
        "medical_necessity_criteria": ["See policy for medical necessity criteria"],
        "common_denial_reasons": ["See policy for denial criteria"],
        "source_section": "default",
    }


class PolicyLookup:
    """Look up prior auth requirements by CPT code and payer (config-driven)."""

    def __init__(self, vector_store: Any = None, cms_lookup: Any = None) -> None:
        self.vector_store = vector_store
        self.cms_lookup = cms_lookup
        self._parsed_base: Path | None = None
        config = get_config()
        paths = config.get("paths", {})
        if paths.get("policies_parsed"):
            base = Path(__file__).resolve().parent.parent.parent
            p = paths["policies_parsed"]
            self._parsed_base = base / p if not Path(p).is_absolute() else Path(p)
        else:
            self._parsed_base = None

    def get_requirements(
        self,
        cpt_code: str,
        payer: str,
        ollama_client: Any = None,
    ) -> dict[str, Any]:
        """
        Get PA requirements for CPT + payer (config-driven routing).

        Flow: normalize payer -> policy_sources config -> cms_api | vector_store | parsed_json -> default.
        When ollama_client is available, rewrites raw policy bullets into staff-friendly language.
        """
        canonical_payer = normalize_payer(payer)
        config = get_config()
        policy_sources = config.get("policy_sources", {})

        source_config = policy_sources.get(canonical_payer)
        if source_config:
            result = self._query_source(source_config, cpt_code, canonical_payer, ollama_client)
            if result:
                return self._maybe_rewrite_for_staff(result, ollama_client)

        result = self._try_generic_parsed_vector(cpt_code, payer, ollama_client)
        if result:
            return self._maybe_rewrite_for_staff(result, ollama_client)
        return _default_requirements()

    def _maybe_rewrite_for_staff(
        self, result: dict[str, Any], ollama_client: Any | None
    ) -> dict[str, Any]:
        """Rewrite raw policy bullets into staff-friendly language when LLM is available."""
        if ollama_client is None:
            return result
        has_content = (
            result.get("documentation_required")
            or result.get("medical_necessity_criteria")
            or result.get("common_denial_reasons")
        )
        if not has_content:
            return result
        return _rewrite_for_staff(result, ollama_client)

    def _query_source(
        self,
        source_config: dict,
        cpt_code: str,
        canonical_payer: str,
        ollama_client: Any,
    ) -> dict[str, Any] | None:
        """Query configured policy source."""
        stype = source_config.get("type")
        if stype == "cms_api":
            if self.cms_lookup is None:
                try:
                    from src.lookup.cms_policy_lookup import CMSPolicyLookup
                    self.cms_lookup = CMSPolicyLookup()
                except Exception:
                    return None
            return self.cms_lookup.get_requirements(cpt_code)

        if stype == "vector_store":
            if not self.vector_store:
                return None
            meta_filter = source_config.get("metadata_filter", {})
            where = meta_filter if meta_filter else None
            chunks = self.vector_store.search(
                f"CPT {cpt_code} prior authorization {canonical_payer}",
                n_results=5,
                where=where,
            )
            if chunks and ollama_client:
                combined = "\n\n".join(c["text"] for c in chunks[:3])
                return self._extract_with_llm(combined[:8000], cpt_code, ollama_client)
            if chunks:
                return self._parse_chunk_to_requirements(chunks[0], cpt_code)
            return None

        if stype == "parsed_json":
            parsed_dir = source_config.get("parsed_dir")
            base = Path(__file__).resolve().parent.parent.parent
            p = Path(parsed_dir) if parsed_dir else base / "data/policies/parsed" / canonical_payer.lower()
            if not p.is_absolute():
                p = base / p
            if p.exists():
                for f in p.glob("*.json"):
                    with open(f, encoding="utf-8") as fp:
                        data = json.load(fp)
                    for chunk in data.get("chunks", []):
                        if cpt_code in chunk.get("text", ""):
                            if ollama_client:
                                return self._extract_with_llm(
                                    chunk["text"], cpt_code, ollama_client
                                )
                            return self._parse_chunk_to_requirements(chunk, cpt_code)
            return None
        return None

    def _try_generic_parsed_vector(
        self, cpt_code: str, payer: str, ollama_client: Any
    ) -> dict[str, Any] | None:
        """Fallback: scan parsed dir and vector store (existing logic)."""
        if self._parsed_base and self._parsed_base.exists():
            for f in self._parsed_base.rglob("*.json"):
                if payer.lower() in f.stem.lower() or payer.lower() in str(f.parent).lower():
                    with open(f, encoding="utf-8") as fp:
                        data = json.load(fp)
                    for chunk in data.get("chunks", []):
                        if cpt_code in chunk.get("text", ""):
                            if ollama_client:
                                return self._extract_with_llm(
                                    chunk["text"], cpt_code, ollama_client
                                )
                            return self._parse_chunk_to_requirements(chunk, cpt_code)
        if self.vector_store:
            query = f"CPT {cpt_code} prior authorization {payer}"
            chunks = self.vector_store.search(query)
            if chunks and ollama_client:
                combined = "\n\n".join(c["text"] for c in chunks[:3])
                return self._extract_with_llm(combined[:8000], cpt_code, ollama_client)
        return None

    def _parse_chunk_to_requirements(self, chunk: dict, cpt_code: str) -> dict[str, Any]:
        """Parse chunk into requirements (simple extraction)."""
        text = chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
        if isinstance(chunk, dict):
            meta = chunk.get("metadata", {})
            source = meta.get("payer", meta.get("source", "parsed"))
        else:
            source = "parsed"
        return {
            "prior_auth_required": "prior auth" in text.lower() or "authorization" in text.lower(),
            "documentation_required": _extract_list_items(text, "documentation", "required"),
            "medical_necessity_criteria": _extract_list_items(text, "criteria", "necessity"),
            "common_denial_reasons": _extract_list_items(text, "denial"),
            "source_section": source,
        }

    def _extract_with_llm(
        self, policy_text: str, cpt_code: str, ollama_client: Any
    ) -> dict[str, Any]:
        """Use LLM to extract requirements from policy text."""
        from src.llm.prompt_manager import format_prompt
        prompt = format_prompt(
            "policy_extractor",
            cpt_code=cpt_code,
            policy_text=policy_text[:8000],
        )
        result = ollama_client.extract_json(prompt)
        return {
            "prior_auth_required": result.get("prior_auth_required", True),
            "documentation_required": result.get("documentation_required", []),
            "medical_necessity_criteria": result.get("medical_necessity_criteria", []),
            "common_denial_reasons": result.get("common_denial_reasons", []),
            "source_section": result.get("source_section", "llm"),
        }


def _rewrite_for_staff(result: dict[str, Any], ollama_client: Any) -> dict[str, Any]:
    """Use LLM to rewrite policy bullets into staff-friendly, actionable language."""
    try:
        from src.llm.prompt_manager import format_prompt
        sub = {
            "documentation_required": result.get("documentation_required", []),
            "medical_necessity_criteria": result.get("medical_necessity_criteria", []),
            "common_denial_reasons": result.get("common_denial_reasons", []),
        }
        requirements_json = json.dumps(sub, indent=2)
        prompt = format_prompt("staff_rewriter", requirements_json=requirements_json)
        out = ollama_client.extract_json(prompt)
        if isinstance(out, dict):
            merged = dict(result)
            if out.get("documentation_required"):
                merged["documentation_required"] = out["documentation_required"]
            if out.get("medical_necessity_criteria"):
                merged["medical_necessity_criteria"] = out["medical_necessity_criteria"]
            if out.get("common_denial_reasons"):
                merged["common_denial_reasons"] = out["common_denial_reasons"]
            return merged
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, Exception):
        pass
    return result


def _extract_list_items(text: str, *keywords: str) -> list[str]:
    """Simple heuristic to extract list items from text."""
    items = []
    lines = str(text).split("\n")
    for line in lines:
        line = line.strip()
        if not line or len(line) < 10:
            continue
        if any(kw in line.lower() for kw in keywords):
            continue
        if line[0] in "-*•" or (len(line) > 2 and line[0].isdigit() and line[1] in ".)"):
            items.append(line.lstrip("-*•0123456789.) ")[:200])
    return items[:10] if items else ["See policy document for details"]
