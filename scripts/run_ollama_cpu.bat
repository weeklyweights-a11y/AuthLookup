@echo off
REM Start Ollama in CPU-only mode (no GPU).
REM Use this if you don't have a GPU or get CUDA allocation errors.
set OLLAMA_NUM_GPU=0
ollama serve
