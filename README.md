# AuthLookup

**Prior Authorization Lookup Tool** — Turn natural language into clear PA requirements in seconds, not hours.

## Demo

<video src="https://raw.githubusercontent.com/weeklyweights-a11y/AuthLookup/master/docs/DEMO.mp4" controls width="640" title="AuthLookup Demo">Your browser does not support the video tag.</video>

---

## The Problem

Before patients can receive many treatments, medications, or procedures, someone must get permission from the insurance company. This permission is called **Prior Authorization (PA)**. Insurance companies require proof that the treatment is medically necessary, that cheaper alternatives were tried first, and that the patient meets specific clinical criteria.

Doctors don't do this work — they're busy seeing patients. The burden falls on **medical assistants, prior authorization specialists, and administrative staff**. These are the unsung heroes who spend their entire day on the phone with insurers, filling out forms, and hunting for information.

### Today's Workflow (Why It's Broken)

1. **Doctor orders** a procedure (e.g., "brain MRI with contrast")
2. **Staff figures out the CPT code** — doctors speak in plain English, insurers speak in codes. There are 10,000+ CPT codes. "Brain MRI with dye" might mean 70551, 70552, or 70553.
3. **Staff finds out if PA is required** — every payer has different rules. Aetna might require PA for brain MRIs; United might not. How do they find out? They Google it.
4. **Staff downloads a 200-page PDF** from the insurer's website, hits Ctrl+F, and scrolls through hundreds of results.
5. **Staff extracts** documentation requirements, medical necessity criteria, and denial reasons from dense policy language.
6. **Only then** can they start the actual prior auth submission.

**Result:** 45+ minutes per prior auth — just for the research phase. Busy clinics handle 50+ PA requests per day. Staff spend **15+ hours per week** on bureaucratic paperwork instead of patient care.

### The Impact

- **Staff:** Burnout, high turnover, repetitive frustrating work
- **Doctors:** Delayed treatments, peer-to-peer calls, administrative burden
- **Patients:** Delayed care (sometimes weeks), confusion, worse health outcomes
- **System:** $31 billion/year on PA administration; 94% of physicians say PA delays necessary care

---

## Our Solution

AuthLookup turns the 45-minute research process into **seconds**:

1. **Type what you need** in plain language: *"brain MRI with contrast, Medicare"*
2. **Get the CPT code** (e.g., 70553) — no manual lookup
3. **Get clear, actionable requirements** — documentation needed, medical necessity criteria, common denial reasons — rewritten in plain language for clinic staff, not cut-and-paste policy legalese

### Before vs After

| Before | After |
|--------|-------|
| Google, PDF downloads, Ctrl+F, 45 min per request | One query → instant answer |
| 200-page policy PDFs | Bullet points staff can act on |
| "Does Blue Cross require PA for this?" — manual hunt | Built-in policy lookup (CMS, configurable payers) |
| Dense legal language | Staff-friendly, actionable bullets |

### Target Users

- Prior authorization specialists
- Medical assistants
- Clinic administrative staff
- Billing and coding teams

---

## Example

**Input:** `brain MRI with contrast, Medicare`

**Output:**
- **CPT Code:** 70553 (MRI brain without contrast, followed by contrast)
- **Prior Auth Required:** Yes
- **Source:** CMS LCD L33632
- **Documentation Needed:** History and physical with neurological exam, clinical indication for contrast, renal function if at risk, prior imaging if follow-up
- **Medical Necessity Criteria:** Known/suspected brain tumor, CNS infection, demyelinating disease, pituitary pathology, post-surgical eval, suspected metastasis
- **Common Denial Reasons:** Contrast not justified, initial headache workup where non-contrast suffices, missing documentation of specific contrast indication

---

## Features

- Natural language input: "brain MRI with contrast, Blue Cross"
- CPT code lookup (keyword + LLM fallback)
- Policy requirement extraction (pre-parsed, vector store, or LLM)
- FHIR CRD and DTR output (CoverageEligibilityResponse, Questionnaire)

## Setup

1. **Python 3.10+** and virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Unix
   # or: venv\Scripts\activate  # Windows
   ```

2. **Install dependencies:**
   ```bash
   pip install -e .
   ```

3. **Ollama** (required):
   ```bash
   ollama pull qwen2.5-coder:3b
   ```
   **CPU-only** (no GPU):
   ```bash
   scripts/run_ollama_cpu.bat   # Windows
   ./scripts/run_ollama_cpu.sh  # Unix
   ```
   Or manually: `set OLLAMA_NUM_GPU=0` (Windows) / `export OLLAMA_NUM_GPU=0` (Unix), then `ollama serve`.

4. **CPT codes (required for procedure lookup):**
   - **From CMS (recommended):** After building the CMS cache (see Optional: CMS below), run:
     ```bash
     python scripts/build_cpt_from_cms.py
     ```
     Builds `data/cpt/cpt_codes.json` from CMS article + LCD CSVs with body-part synonym keywords so queries like "MRI of the knee" map to the correct code (73721).
   - **Alternative:** `python scripts/fetch_cpt_data.py` (imaging subset from external Gist).

5. **Run the app:**
   ```bash
   streamlit run src/api/streamlit_app.py
   ```

## Optional: CMS and Policy Data

**CMS Medicare coverage (recommended):**
- **From bulk download:** Place `current_article.zip` (and optionally `current_lcd.zip`) in `data/cms/`, unzip, then run:
  ```bash
  python scripts/build_cms_cache_from_bulk.py
  python scripts/build_cpt_from_cms.py
  ```
  The first builds `data/cms/articles_cache.json`; the second builds `data/cpt/cpt_codes.json` from the same CMS data so procedure→CPT only returns codes we have policy for.
- **From API:** `python scripts/fetch_cms_coverage.py` (requires CMS license token).

**Policy PDFs (any payer):**
Configure `policy_pdfs` in `config/default.yaml`, then:
```bash
python scripts/fetch_policy_pdfs.py
python scripts/parse_policy_pdfs.py --payer UnitedHealthcare
python scripts/seed_vector_db.py
```

**Adding a new payer:** Add payer + URLs to `policy_pdfs` and an entry to `policy_sources` in config. No code changes needed.

## Architecture

AuthLookup uses a **RAG (Retrieval Augmented Generation)** pipeline: retrieve policy data, then use an LLM to parse, extract, and rewrite for staff.

### End-to-end flow

```
Query: "brain MRI with contrast, Medicare"
    │
    ├─► 1. Input parsing (LLM)     → procedure, payer
    ├─► 2. CPT lookup              → 70553 (keyword + LLM fallback)
    ├─► 3. Policy retrieval        → config-driven by payer
    ├─► 4. Staff rewrite (LLM)     → plain-language bullets
    └─► 5. FHIR generation         → CRD + DTR JSON
```

### RAG components

| Layer | Module | Role |
|-------|--------|------|
| **Input parsing** | `ollama_client` + `input_parser` prompt | Extract procedure + payer from natural language |
| **CPT lookup** | `cpt_lookup.py` | Keyword matching (body-part alignment, modality scoring) → LLM fallback (`cpt_mapper` prompt) |
| **Policy retrieval** | Config-driven: `cms_api`, `vector_store`, `parsed_json` | Fetch requirements for CPT + payer |
| **CMS cache** | `cms_policy_lookup.py` + `articles_cache.json` | Pre-built from CMS bulk CSV (articles + LCDs) |
| **Vector store** | `vector_store.py` (ChromaDB) | Semantic search over policy PDF chunks |
| **Parsed JSON** | `policy_lookup.py` | File-based scan of `data/policies/parsed/{payer}/*.json` |
| **LLM extraction** | `policy_extractor` prompt | Extract structured requirements from retrieved chunks (when using vector_store) |
| **Staff rewrite** | `staff_rewriter` prompt | Rewrite raw policy bullets into actionable language |
| **FHIR** | `crd_generator.py`, `dtr_generator.py` | CoverageEligibilityResponse, Questionnaire |

### Ingestion (offline)

| Script / module | Purpose |
|-----------------|---------|
| `build_cms_cache_from_bulk.py` | CMS article + LCD CSVs → `articles_cache.json` (CPT → requirements) |
| `build_cpt_from_cms.py` | CMS data → `cpt_codes.json` (keywords, body-part synonyms) |
| `fetch_policy_pdfs.py` | Download payer policy PDFs |
| `pdf_parser.py` | PDF text extraction (PyMuPDF) |
| `parse_policy_pdfs.py` | PDF → parsed chunks (uses pdf_parser + policy_chunker) |
| `policy_chunker.py` | Chunk sizing, overlap |
| `seed_vector_db.py` | Parsed chunks → ChromaDB (embed + store) |

### Policy sources (config-driven)

- **Medicare** → `cms_api` (articles_cache.json)
- **UnitedHealthcare, Aetna** → `vector_store` (ChromaDB)
- **Anthem** → `parsed_json` (JSON files)

Add payers in `config/default.yaml` under `policy_sources` — no code changes needed.

## Troubleshooting

**CPU-only setup:** Use `scripts/run_ollama_cpu.bat` (Windows) or `./scripts/run_ollama_cpu.sh` (Unix) to start Ollama without GPU.

**"unable to allocate CUDA_Host buffer":** Force CPU mode with `OLLAMA_NUM_GPU=0` before starting Ollama. Logs: `%LOCALAPPDATA%\Ollama\server.log`

See [docs/REFERENCE_MAP.md](docs/REFERENCE_MAP.md) for reference repository mapping. AuthLookup integrates body-part synonym logic (knee/lower extremity, head/neck, spine) in `build_cpt_from_cms.py` and `cpt_lookup.py`.
