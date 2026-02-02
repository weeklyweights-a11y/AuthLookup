"""Streamlit application for AuthLookup."""

import json
import streamlit as st

from src.lookup.cpt_lookup import CPTLookup
from src.lookup.policy_lookup import PolicyLookup
from src.fhir.crd_generator import generate_crd_response
from src.fhir.dtr_generator import generate_dtr_questionnaire


def main() -> None:
    import subprocess
    import sys
    subprocess.run([sys.executable, "-m", "streamlit", "run", __file__, *sys.argv[1:]], check=True)


def get_ollama_client():
    """Get OllamaClient. Raises if Ollama is unavailable."""
    from src.llm.ollama_client import OllamaClient
    return OllamaClient()


def check_ollama_available() -> tuple[bool, str]:
    """Check if Ollama is running and reachable. Returns (ok, error_message)."""
    try:
        client = get_ollama_client()
        client.query("ok")
        return True, ""
    except ImportError as e:
        return False, f"ollama package required. Install with: pip install ollama"
    except Exception as e:
        return False, f"Ollama not available: {e}. Start Ollama (ollama serve) and pull the model (ollama pull qwen2.5-coder:3b)."


def parse_input_with_llm(query: str, client):
    """Parse procedure and payer from query using LLM."""
    from src.llm.prompt_manager import format_prompt
    prompt = format_prompt("input_parser", query=query)
    result = client.extract_json(prompt)
    return result.get("procedure", query), result.get("payer", "Unknown")


def run_app() -> None:
    st.set_page_config(page_title="AuthLookup", page_icon="\U0001f3e5")
    st.title("AuthLookup")
    st.caption("Prior Authorization Lookup - Natural language to PA requirements")

    ollama_ok, ollama_error = check_ollama_available()
    if not ollama_ok:
        st.error(f"**Ollama is required.** {ollama_error}")
        st.info("Run `ollama pull qwen2.5-coder:3b` then `scripts/run_ollama_cpu.bat` (or `ollama serve` with CPU).")
        return

    query = st.text_input(
        "What do you need?",
        placeholder="e.g., brain MRI with contrast, Blue Cross",
    )

    if st.button("Search", type="primary") and query:
        with st.spinner("Looking up requirements..."):
            try:
                client = get_ollama_client()
                procedure, payer = parse_input_with_llm(query, client)
                cpt_lookup = CPTLookup()
                cpt_result = cpt_lookup.find_code_with_llm(procedure or query, client)

                if not cpt_result.get("code"):
                    st.error("Could not map procedure to CPT code. Try being more specific.")
                    return

                policy_lookup = PolicyLookup()
                requirements = policy_lookup.get_requirements(cpt_result["code"], payer, client)

                # Results full-width (primary focus for staff)
                st.subheader("Results")
                m1, m2 = st.columns(2)
                with m1:
                    st.metric("CPT Code", cpt_result["code"])
                with m2:
                    st.metric("Prior Auth Required", "Yes" if requirements.get("prior_auth_required") else "No")
                source = requirements.get("source_section", "unknown")
                st.caption(f"Source: {source}")
                st.write("**Documentation Needed:**")
                for doc in requirements.get("documentation_required", []):
                    st.write(f"- {doc}")
                st.write("**Common Denial Reasons:**")
                for r in requirements.get("common_denial_reasons", []):
                    st.write(f"- {r}")

                # FHIR output in expander (secondary, for system integration)
                crd = generate_crd_response(cpt_result["code"], requirements)
                dtr = generate_dtr_questionnaire(cpt_result["code"], requirements)
                with st.expander("FHIR Output (for EHR / system integration)"):
                    tab1, tab2 = st.tabs(["CRD Response", "DTR Questionnaire"])
                    with tab1:
                        st.json(crd)
                        st.download_button("Download CRD JSON", json.dumps(crd, indent=2), "crd_response.json")
                    with tab2:
                        st.json(dtr)
                        st.download_button("Download DTR JSON", json.dumps(dtr, indent=2), "dtr_questionnaire.json")

            except Exception as e:
                st.error(f"Error: {e}")


if __name__ == "__main__":
    run_app()
