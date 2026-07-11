"""
CV parsing: PDF and DOCX extraction, text chunking, and name heuristics.

Supported formats: .pdf, .docx
Unsupported formats: skipped with a log warning (never raises).

Chunking strategy: fixed word-count windows with overlap.
This is intentionally simple and robust across 20,000+ heterogeneous CVs.
Section-based parsing is fragile; fixed chunking is reliable.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".docx"})

CHUNK_WORD_SIZE = 400   # words per chunk
CHUNK_OVERLAP   = 50    # words of overlap between adjacent chunks

# Keywords that indicate a line is a section header, not a name
_HEADER_KEYWORDS = frozenset({
    "resume", "cv", "curriculum", "vitae", "profile", "summary",
    "objective", "contact", "address", "education", "experience",
    "skills", "projects", "references", "declaration",
})


# ── Data Structures ────────────────────────────────────────────────────────────

@dataclass
class ParsedCV:
    """Result of parsing a single CV file."""
    candidate_id: str
    name: str
    cv_path: str
    raw_text: str
    chunks: list[str] = field(default_factory=list)


# ── Internal Helpers ───────────────────────────────────────────────────────────

def _extract_name(text: str, filename_stem: str) -> str:
    """
    Heuristic name extraction: look for a 2–4 word capitalised line
    near the top of the CV. Falls back to a cleaned-up filename stem.
    """
    for line in text.splitlines()[:15]:          # Only inspect first 15 lines
        line = line.strip()
        if not line:
            continue
        words = line.split()
        if 2 <= len(words) <= 4:
            # All words should start with a capital letter
            if all(w[0].isupper() for w in words if w and w[0].isalpha()):
                # Reject obvious header lines
                if not any(kw in line.lower() for kw in _HEADER_KEYWORDS):
                    # Reject lines with special characters common in headers
                    if not any(ch in line for ch in (":", "|", "/", "@", "–", "-")):
                        return line

    # Fallback: derive from filename
    stem = filename_stem.replace("_", " ").replace("-", " ")
    return " ".join(w.capitalize() for w in stem.split())


def _chunk_text(text: str, chunk_size: int = CHUNK_WORD_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping fixed-size word chunks.
    Empty or very short texts return a single chunk.
    """
    words = text.split()
    if not words:
        return []
    if len(words) <= chunk_size:
        return [" ".join(words)]

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end >= len(words):
            break
        start = end - overlap

    return chunks


def _parse_pdf(path: Path) -> str:
    """Extract plain text from a PDF using pdfplumber."""
    import pdfplumber  # type: ignore

    pages: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    return "\n".join(pages)


def _parse_docx(path: Path) -> str:
    """Extract plain text from a DOCX file."""
    from docx import Document  # type: ignore

    doc = Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


# ── Public API ─────────────────────────────────────────────────────────────────

def parse_file(path: Path, candidate_id: str) -> Optional[ParsedCV]:
    """
    Parse a CV file into a ParsedCV object.

    Returns:
        ParsedCV if the file was successfully parsed and contains text.
        None if the file type is unsupported or the file yields no text.

    Raises:
        Any exception from the underlying parser — the caller (run.py) is
        responsible for catching, logging, and continuing to the next file.
    """
    ext = path.suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        logger.warning("Unsupported file type skipped: %s (%s)", path.name, ext)
        return None

    if ext == ".pdf":
        raw_text = _parse_pdf(path)
    else:  # .docx
        raw_text = _parse_docx(path)

    if not raw_text or not raw_text.strip():
        logger.warning(
            "No text extracted from %s — may be a scanned/image-only PDF. Skipping.",
            path.name,
        )
        return None

    name = _extract_name(raw_text, path.stem)
    chunks = _chunk_text(raw_text)

    logger.debug(
        "Parsed '%s' → name='%s', %d words, %d chunks",
        path.name,
        name,
        len(raw_text.split()),
        len(chunks),
    )

    return ParsedCV(
        candidate_id=candidate_id,
        name=name,
        cv_path=str(path),
        raw_text=raw_text,
        chunks=chunks,
    )
