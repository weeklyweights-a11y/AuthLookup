"""Chunk policy text for vector store ingestion."""

from dataclasses import dataclass

from src.ingestion.pdf_parser import ParsedPdf


@dataclass
class PolicyChunk:
    """A chunk of policy text with metadata."""

    text: str
    chunk_index: int
    page_number: int | None
    metadata: dict


def chunk_policy(
    parsed: ParsedPdf,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    payer: str | None = None,
    source_file: str | None = None,
) -> list[PolicyChunk]:
    """
    Split parsed policy text into overlapping chunks.

    Args:
        parsed: Parsed PDF result.
        chunk_size: Max characters per chunk.
        chunk_overlap: Overlap between consecutive chunks.
        payer: Payer name for metadata.
        source_file: Source filename for metadata.

    Returns:
        List of PolicyChunk with text and metadata.
    """
    chunks: list[PolicyChunk] = []
    text = parsed.full_text
    metadata_base = {
        "payer": payer or "unknown",
        "source": source_file or parsed.title,
    }

    start = 0
    chunk_index = 0

    while start < len(text):
        end = start + chunk_size
        chunk_text = text[start:end]

        if not chunk_text.strip():
            start = end - chunk_overlap
            continue

        page_num = _estimate_page_for_position(text, parsed, start)

        chunks.append(
            PolicyChunk(
                text=chunk_text.strip(),
                chunk_index=chunk_index,
                page_number=page_num,
                metadata={
                    **metadata_base,
                    "chunk_index": chunk_index,
                    "page": page_num,
                },
            )
        )
        chunk_index += 1
        start = end - chunk_overlap

    return chunks


def _estimate_page_for_position(full_text: str, parsed: ParsedPdf, position: int) -> int | None:
    """Estimate which page a character position falls in."""
    cumul = 0
    for i, page in enumerate(parsed.pages):
        cumul += len(page.text) + 2
        if position < cumul:
            return page.page_number
    return parsed.pages[-1].page_number if parsed.pages else None
