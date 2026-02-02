"""
Fetch policy PDFs for payers from config.

Reads policy_pdfs from config, downloads to data/policies/raw/{payer}/.
Run: python scripts/fetch_policy_pdfs.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from src.config import get_config


def main() -> int:
    config = get_config()
    policy_pdfs = config.get("policy_pdfs", {})
    base = Path(__file__).resolve().parent.parent
    raw_path = config.get("paths", {}).get("policies_raw", "data/policies/raw")
    raw_base = Path(raw_path) if Path(raw_path).is_absolute() else base / raw_path

    if not policy_pdfs:
        print("No policy_pdfs configured. Add payer URLs to config.")
        return 0

    for payer, urls in policy_pdfs.items():
        if not urls:
            continue
        payer_dir = raw_base / payer.lower().replace(" ", "_")
        payer_dir.mkdir(parents=True, exist_ok=True)
        for url in urls:
            try:
                resp = requests.get(url, timeout=60, stream=True)
                resp.raise_for_status()
                name = url.split("/")[-1].split("?")[0] or "policy.pdf"
                if not name.lower().endswith(".pdf"):
                    name += ".pdf"
                out_path = payer_dir / name
                with open(out_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"Downloaded {payer}: {out_path.name}")
            except Exception as e:
                print(f"Error {payer} {url}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
