# AuthLookup Copilot Instructions

## Project Overview

**AuthLookup** converts natural language healthcare queries into structured Prior Authorization (PA) requirements using a local LLM (Ollama). It maps medical procedures to CPT codes and extracts policy requirements from multiple sources, outputting FHIR-compliant responses.

**Core flow:** Natural language → CPT code lookup → Policy requirement extraction → FHIR CRD/DTR JSON output

## Architecture Patterns

### Component Organization

- **`src/api/streamlit_app.py`**: UI entry point (runs full Streamlit lifecycle)
- **`src/lookup/`**: Core lookup engines:
  - `cpt_lookup.py`: Keyword-based + LLM-fallback CPT code mapping
  - `policy_lookup.py`: Config-driven policy requirement routing
  - `vector_store.py`: ChromaDB wrapper for parsed policies
  - `payer_aliases.py`: Canonical payer name normalization
- **`src/llm/`**: LLM integration (Ollama only, no OpenAI):
  - `ollama_client.py`: HTTP client with JSON extraction via regex
  - `prompt_manager.py`: Template-based prompts from `config/prompts/`
- **`src/fhir/`**: FHIR resource generation (CoverageEligibilityResponse, Questionnaire)
- **`src/ingestion/`**: Data pipeline (PDF parsing, chunking, vector seeding)

### Configuration Pattern (YAML-driven)

All behavior is controlled via **`config/default.yaml`** (no hardcoded routes):

- **`policy_sources`**: Maps payer to lookup strategy (cms_api, vector_store, parsed_json)
- **`payer_aliases`**: Normalizes "united" → "UnitedHealthcare", "medicare" → "Medicare"
- **`paths`**: Auto-resolved relative to project root
- **Environment overrides**: `AUTHLOOKUP_OLLAMA_MODEL`, `AUTHLOOKUP_OLLAMA_BASE_URL`

**Key insight:** Adding a new payer requires ONLY config changes—update `policy_sources` and `payer_aliases`, no code edits.

### Policy Lookup Strategy

[PolicyLookup.get_requirements()](src/lookup/policy_lookup.py#L45) applies this cascade:

1. Normalize payer name → lookup `policy_sources[canonical_payer]`
2. Query configured source (CMS API, vector store, or parsed JSON directory)
3. Fall back to generic parsed/vector data if payer-specific source fails
4. Return sensible defaults if all else fails

This isolation allows each policy source to fail independently without cascading.

## Critical Developer Workflows

### Setup (CPU-only, no GPU)

```bash
python -m venv venv
source venv/bin/activate    # Unix: venv\Scripts\activate (Windows)
pip install -e .
ollama pull qwen2.5-coder:3b
python scripts/fetch_cpt_data.py

# For CPU-only Ollama:
scripts/run_ollama_cpu.bat  # Windows: sets OLLAMA_NUM_GPU=0
# or Unix: ./scripts/run_ollama_cpu.sh
```

### Development & Testing

```bash
pytest tests/                    # All tests (no Ollama required)
pytest tests/test_integration.py # End-to-end without Ollama
streamlit run src/api/streamlit_app.py  # Interactive UI
```

### Adding Policy Data

1. **Pre-parsed JSON** (fastest):
   ```bash
   # Add payer to policy_sources in config/default.yaml
   # policy_sources:
   #   NewPayer:
   #     type: parsed_json
   #     parsed_dir: "data/policies/parsed/newpayer"
   ```

2. **Vector store** (from PDFs):
   ```bash
   python scripts/fetch_policy_pdfs.py   # Configure URLs in config
   python scripts/parse_policy_pdfs.py --payer UnitedHealthcare
   python scripts/seed_vector_db.py
   ```

3. **CMS API**: Auto-configured for Medicare (requires cache or live fetch)

## Key Code Patterns

### LLM Fallback (Graceful Degradation)

```python
# CPTLookup.find_code_with_llm() pattern:
# 1. Try keyword match
# 2. If low confidence, ask LLM (with CPT list context)
# 3. Validate LLM output against known codes
# 4. Return keyword result if all else fails
```

This ensures the app runs without Ollama (unit tests verify this).

### Config-Driven Routing

```python
# PolicyLookup doesn't hardcode "if payer == X, use Y"
# Instead: read config, dispatch to _query_source(source_config, ...)
# Makes it trivial to add payers without code changes
```

### Payer Name Normalization

Always call [normalize_payer()](src/lookup/payer_aliases.py) before lookups to handle aliases ("united" → "UnitedHealthcare").

## Testing Strategy

- **Unit tests** (no Ollama): CPT lookup, policy lookup, FHIR generators, config loading
- **Integration test**: [test_integration.py](tests/test_integration.py) validates full flow without Ollama
- **Mocking**: Use `conftest.py` fixtures (e.g., mock_ollama) to avoid live LLM calls
- **Coverage**: `pytest --cov=src` targets 70%+ on core lookup logic

## External Dependencies

- **Ollama** (local LLM): Default model `qwen2.5-coder:3b` (3B params, CPU-friendly)
- **ChromaDB** (vector store): For parsed policy retrieval
- **Streamlit**: Web UI (run on `localhost:8501`)
- **PyMuPDF**: PDF parsing (policy ingestion)
- **CMS API**: Optional (Medicare coverage lookup)

## Common Pitfalls & Fixes

| Issue | Fix |
|-------|-----|
| "Ollama not available" | Run `ollama serve` or use `run_ollama_cpu.bat` |
| CUDA allocation errors | Set `OLLAMA_NUM_GPU=0` before Ollama start |
| Low CPT match confidence | Ensure `data/cpt/cpt_codes.json` is populated (`fetch_cpt_data.py`) |
| Policy requirements always "default" | Verify payer is in `policy_sources` and data exists in `data/policies/` |
| Config path not found | Paths resolve relative to project root; check `config/default.yaml` |

## File Locations to Know

- **Prompts** (LLM templates): `config/prompts/{input_parser,cpt_mapper,policy_extractor}.txt`
- **CPT data**: `data/cpt/cpt_codes.json` (indexed by keyword at runtime)
- **Parsed policies**: `data/policies/parsed/{payer}/` (JSON per CPT code)
- **FHIR templates**: `data/fhir_templates/crd_template.json`
- **Vector DB**: `chroma_db/` (created by `seed_vector_db.py`)
