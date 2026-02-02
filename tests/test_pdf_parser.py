"""Tests for PDF parser."""

import pytest

pytest.importorskip("fitz", reason="pymupdf not installed")

from src.ingestion.pdf_parser import extract_text_from_pdf, ParsedPdf


def test_extract_nonexistent_pdf_raises():
    """Non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="not found"):
        extract_text_from_pdf("/nonexistent/file.pdf")


def test_extract_non_pdf_raises():
    """Non-PDF file raises ValueError."""
    with pytest.raises(ValueError, match="Not a PDF"):
        extract_text_from_pdf(__file__)


def test_chunker_with_parsed_pdf():
    """Chunker produces chunks from parsed PDF."""
    from src.ingestion.policy_chunker import chunk_policy

    # Create a minimal mock ParsedPdf
    class MockPage:
        page_number = 1
        text = "Sample text"
        metadata = {"page": 1}

    parsed = ParsedPdf(
        path="test.pdf",
        title="test",
        pages=[MockPage(), MockPage()],
        full_text="Sample policy text. " * 100,
    )
    chunks = chunk_policy(parsed, chunk_size=50, chunk_overlap=10)
    assert len(chunks) >= 1
    assert chunks[0].text
    assert chunks[0].metadata.get("payer") == "unknown"
