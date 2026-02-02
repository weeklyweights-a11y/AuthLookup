"""
Batch parse policy PDFs and save to data/policies/parsed/.

Usage:
    python scripts/parse_policy_pdfs.py [--input-dir data/policies/raw]
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ingestion.pdf_parser import extract_text_from_pdf
from src.ingestion.policy_chunker import chunk_policy
from src.lookup.payer_aliases import normalize_payer


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-dir",
        default="data/policies/raw",
        help="Directory containing PDF files",
    )
    parser.add_argument(
        "--output-dir",
        default="data/policies/parsed",
        help="Output directory for parsed JSON",
    )
    parser.add_argument(
        "--payer",
        default=None,
        help="Canonical payer name (e.g. UnitedHealthcare). Infer from filename if omitted.",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent.parent
    input_dir = base_dir / args.input_dir
    output_dir = base_dir / args.output_dir

    if not input_dir.exists():
        print(f"Input directory not found: {input_dir}")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_files = list(input_dir.rglob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {input_dir}")
        print("Add policy PDFs to the raw directory.")
        return 0

    for pdf_path in pdf_files:
        try:
            parsed = extract_text_from_pdf(pdf_path)
            raw_payer = args.payer or (pdf_path.stem.split("_")[0] if "_" in pdf_path.stem else pdf_path.parent.name)
            canonical_payer = normalize_payer(raw_payer)
            chunks = chunk_policy(
                parsed,
                payer=canonical_payer,
                source_file=pdf_path.name,
            )
            output = {
                "source": pdf_path.name,
                "title": parsed.title,
                "page_count": parsed.page_count,
                "chunks": [
                    {
                        "text": c.text,
                        "chunk_index": c.chunk_index,
                        "page": c.page_number,
                        "metadata": c.metadata,
                    }
                    for c in chunks
                ],
            }
            payer_subdir = output_dir / canonical_payer.lower().replace(" ", "_")
            payer_subdir.mkdir(parents=True, exist_ok=True)
            out_path = payer_subdir / f"{pdf_path.stem}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2)
            print(f"Parsed {pdf_path.name} -> {out_path.name} ({len(chunks)} chunks)")
        except Exception as e:
            print(f"Error parsing {pdf_path.name}: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
