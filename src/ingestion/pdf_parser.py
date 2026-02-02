"""PDF text extraction using PyMuPDF."""

from pathlib import Path
from dataclasses import dataclass

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


@dataclass
class ParsedPage:
    """Single page from a PDF."""

    page_number: int
    text: str
    metadata: dict


@dataclass
class ParsedPdf:
    """Parsed PDF document."""

    path: str
    title: str
    pages: list[ParsedPage]
    full_text: str

    @property
    def page_count(self) -> int:
        return len(self.pages)


def extract_text_from_pdf(pdf_path: str | Path) -> ParsedPdf:
    """
    Extract text from a PDF file.

    Args:
        pdf_path: Path to PDF file.

    Returns:
        ParsedPdf with pages and full text.

    Raises:
        FileNotFoundError: If PDF does not exist.
        ValueError: If file is not a valid PDF.
    """
    if fitz is None:
        raise ImportError("PyMuPDF (pymupdf) is required. Install with: pip install pymupdf")

    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Not a PDF file: {path}")

    try:
        doc = fitz.open(path)
    except Exception as e:
        raise ValueError(f"Invalid or corrupted PDF: {path}") from e

    pages: list[ParsedPage] = []
    full_text_parts: list[str] = []

    try:
        for i in range(len(doc)):
            page = doc[i]
            text = page.get_text()
            pages.append(
                ParsedPage(
                    page_number=i + 1,
                    text=text,
                    metadata={"page": i + 1},
                )
            )
            full_text_parts.append(text)
    finally:
        doc.close()

    title = path.stem
    full_text = "\n\n".join(full_text_parts)

    return ParsedPdf(
        path=str(path),
        title=title,
        pages=pages,
        full_text=full_text,
    )
