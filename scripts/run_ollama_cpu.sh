#!/bin/sh
# Start Ollama in CPU-only mode (no GPU).
# Use this if you don't have a GPU or get CUDA allocation errors.
export OLLAMA_NUM_GPU=0
ollama serve
