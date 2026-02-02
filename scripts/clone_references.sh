#!/bin/bash
set -e
mkdir -p references && cd references
git clone --depth 1 https://github.com/HL7-DaVinci/CDS-Library.git
git clone --depth 1 https://github.com/HL7-DaVinci/CRD.git
git clone --depth 1 https://github.com/HL7-DaVinci/dtr.git
git clone --depth 1 https://github.com/HL7-DaVinci/prior-auth.git
git clone --depth 1 https://github.com/digithree/ollama-rag.git
git clone --depth 1 https://github.com/QuivrHQ/MegaParse.git
git clone --depth 1 https://github.com/AlgorexHealth/cms-code-categorizer-python.git
git clone --depth 1 https://github.com/nhs-pycom/nhs-streamlit-template.git
git clone --depth 1 https://github.com/abhijeetk597/medical-data-extraction.git
git clone --depth 1 https://github.com/cpepper96/ollama-local-rag.git
git clone --depth 1 https://github.com/jennis0/burdoc.git
cd ..
echo "All 11 reference repositories cloned to references/"
