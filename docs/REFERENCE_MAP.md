# AuthLookup Reference Map

Maps reference repository files to AuthLookup modules. Use this when implementing each phase.

## Phase 2: Ingestion Module

| Our Module | Reference File | What to Copy/Adapt |
|------------|----------------|-------------------|
| `pdf_parser.py` | `references/ollama-rag/pdf_ingest.py` | PDF loading, chunking pattern |
| `pdf_parser.py` | `references/MegaParse/` | LLM-optimized parsing if PyMuPDF insufficient |
| `policy_chunker.py` | `references/ollama-rag/pdf_ingest.py` | Chunk sizing, overlap logic |
| `parse_policy_pdfs.py` | `references/medical-data-extraction/` | Batch extraction pipeline |

## Phase 3: LLM Layer

| Our Module | Reference File | What to Copy/Adapt |
|------------|----------------|-------------------|
| `ollama_client.py` | `references/ollama-rag/chat.py` | Ollama HTTP calls, streaming |
| `ollama_client.py` | `references/ollama-local-rag/` | Simple query pattern |
| `json_extractor.py` | N/A | Custom regex + validation for structured output |

## Phase 4: Lookup Modules

| Our Module | Reference File | What to Copy/Adapt |
|------------|----------------|-------------------|
| `vector_store.py` | `references/ollama-rag/` | ChromaDB setup, embedding, search |
| `cpt_lookup.py` | `references/cms-code-categorizer-python/` | CPT categorization, code families |
| `policy_lookup.py` | `references/ollama-rag/chat.py` | RAG retrieval flow |

## Phase 5: FHIR Generation

| Our Module | Reference File | What to Copy/Adapt |
|------------|----------------|-------------------|
| `crd_template.json` | `references/CDS-Library/CRD-DTR/HomeOxygenTherapy/R4/crd/*.json` | CoverageEligibilityResponse structure |
| `dtr_template.json` | `references/CDS-Library/CRD-DTR/HomeOxygenTherapy/R4/dtr/*.json` | Questionnaire structure |
| `crd_generator.py` | `references/CRD/` | CRD response patterns |
| `dtr_generator.py` | `references/dtr/` | Questionnaire item building |

## Phase 6: Streamlit UI

| Our Module | Reference File | What to Copy/Adapt |
|------------|----------------|-------------------|
| `streamlit_app.py` | `references/ollama-rag/streamlit_app.py` | Layout, chat flow |
| UI styling | `references/nhs-streamlit-template/` | Healthcare theme, colors |
