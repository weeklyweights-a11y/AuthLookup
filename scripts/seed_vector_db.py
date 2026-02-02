"""
Seed ChromaDB with policy chunks from parsed JSON files.

Run after parse_policy_pdfs.py. Requires parsed JSON in data/policies/parsed/.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import get_config
from src.lookup.vector_store import PolicyVectorStore


def main() -> int:
    config = get_config()
    base = Path(__file__).resolve().parent.parent
    parsed_dir = base / config.get("paths", {}).get("policies_parsed", "data/policies/parsed")

    if not parsed_dir.exists():
        print(f"Parsed directory not found: {parsed_dir}")
        return 1

    json_files = list(parsed_dir.rglob("*.json"))
    if not json_files:
        print("No parsed JSON files found. Run parse_policy_pdfs.py first.")
        return 0

    store = PolicyVectorStore()
    total = 0
    for jf in json_files:
        with open(jf, encoding="utf-8") as f:
            data = json.load(f)
        chunks = data.get("chunks", [])
        if chunks:
            ids = [f"{jf.stem}_{c['chunk_index']}" for c in chunks]
            store.add_chunks(chunks, ids=ids)
            total += len(chunks)
            print(f"Added {len(chunks)} chunks from {jf.name}")
    print(f"Total: {total} chunks in vector store")
    return 0


if __name__ == "__main__":
    sys.exit(main())
