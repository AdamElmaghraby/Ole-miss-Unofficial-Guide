"""
ingest.py — Milestone 3: Ingestion & Chunking for the RAG system.

This script:
  1. Loads every .txt file in the documents/ directory.
  2. Cleans out common Reddit UI noise line-by-line and drops empty lines.
  3. Splits the cleaned text into overlapping chunks with LangChain's
     RecursiveCharacterTextSplitter (size=500, overlap=100).
  4. Attaches the source filename as metadata to every chunk.

Run directly (`python ingest.py`) to execute the verification block at the
bottom, which prints the total chunk count and 5 random chunks for inspection.

Requires: pip install langchain-text-splitters   (or the full `langchain` package)
"""

import os
import random
import re

# LangChain split the text splitters into their own lightweight package
# (langchain-text-splitters). Fall back to the legacy location so this works
# regardless of which LangChain version is installed.
try:
    from langchain_text_splitters import (
        RecursiveCharacterTextSplitter,
        MarkdownHeaderTextSplitter,
    )
except ImportError:  # older LangChain versions
    from langchain.text_splitter import (
        RecursiveCharacterTextSplitter,
        MarkdownHeaderTextSplitter,
    )

# We build plain Document-like chunks. Importing LangChain's Document keeps the
# output compatible with downstream vector-store loaders; fall back to a tiny
# stand-in if the core package isn't available.
try:
    from langchain_core.documents import Document
except ImportError:  # pragma: no cover - fallback for minimal installs
    class Document:
        """Minimal stand-in mirroring LangChain's Document interface."""

        def __init__(self, page_content, metadata=None):
            self.page_content = page_content
            self.metadata = metadata or {}


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Folder holding the raw .txt files, resolved relative to this script so it
# works no matter where the script is invoked from.
DOCUMENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documents")

# Chunking parameters required by the milestone spec.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

# --- Tier 1: substring keywords -------------------------------------------
# Lower-cased substrings. A line is dropped if it CONTAINS any of these.
# Only include phrases distinctive enough that they won't appear inside a
# genuine comment (mostly full UI labels and multi-word chrome strings).
NOISE_KEYWORDS = (
    # Original action buttons.
    "reply",
    "share",
    "report",
    "save",
    "give award",
    "permalink",
    "upvote",                       # matches "upvote", "upvotes", "upvoted"
    # Navigation / page chrome.
    "skip to main content",
    "skip to navigation",
    "skip to right sidebar",
    "expand user menu",
    "collapse navigation",
    "comments section",
    "community info section",
    "view post in",
    "avatar",                       # "u/<name> avatar" lines
    # Auth / signup prompts.
    "new to reddit",
    "create your account and connect",
    "continue with phone number",
    "by continuing, you agree",
    # Related-posts / discovery widgets.
    "people also ask",
    "rereddit",                     # "reReddit: Top posts of 2024"
    # Footer / legal.
    "reddit rules",
    "privacy policy",
    "user agreement",
    "your privacy choices",
    "all rights reserved",
    "reddit, inc",
    # Deleted/removed placeholders.
    "[deleted]",
    "[removed]",
)

# --- Tier 2: exact full-line matches --------------------------------------
# Short tokens that are pure UI when they're the WHOLE line, but would wreck
# real content if matched as substrings (e.g. "back", "join", "public",
# "reddit", "ago"). Compared case-insensitively against the whole stripped line.
NOISE_EXACT = {
    "•",                       # • bullet
    "·",                       # · middot
    "op",
    "back",
    "join",
    "public",
    "reddit",
    "sign up",
    "log in",
    "see more",
    "top posts",
    "accessibility",
    "go to olemiss",
    "ole miss and oxford",
    "mississippi's oldest and finest university",
}

# --- Tier 3: regex patterns (matched against the stripped line) -----------
# Structural noise whose exact text varies but whose shape is predictable.
NOISE_PATTERNS = (
    re.compile(r"^r/\w+", re.IGNORECASE),                       # subreddit refs / cross-posted titles
    re.compile(r"^u/\w+", re.IGNORECASE),                       # username header lines
    re.compile(r"^search in\b", re.IGNORECASE),                 # "Search in r/olemiss"
    re.compile(r"^-?\d+$"),                                     # bare vote/score counts: 1, 3, -1
    re.compile(r"^\d+\s*comments?$", re.IGNORECASE),            # "8 Comments", "1 comment"
    re.compile(                                                 # relative timestamps: "2y ago", "10mo ago"
        r"^\d+\s*(y|yr|yrs|mo|mos|w|wk|wks|d|h|hr|hrs|m|min|mins|s|sec)\s*ago$",
        re.IGNORECASE,
    ),
)


# ---------------------------------------------------------------------------
# Step 1: Ingestion & automated cleaning
# ---------------------------------------------------------------------------

def clean_text(raw_text):
    """Strip Reddit UI noise from a block of raw text.

    Processes the text line-by-line, dropping a line if it is:
      - empty / whitespace-only,
      - an exact UI label (NOISE_EXACT),
      - containing a noise keyword (NOISE_KEYWORDS), or
      - matching a structural noise pattern (NOISE_PATTERNS).

    Returns the cleaned text as a single string with one kept line per row.
    """
    kept_lines = []
    for line in raw_text.splitlines():
        stripped = line.strip()

        # Skip empty lines.
        if not stripped:
            continue

        lowered = stripped.lower()

        # Tier 2: drop short UI tokens only when they are the entire line.
        if lowered in NOISE_EXACT:
            continue

        # Tier 1: drop lines containing a distinctive noise keyword.
        if any(keyword in lowered for keyword in NOISE_KEYWORDS):
            continue

        # Tier 3: drop lines matching a structural noise pattern.
        if any(pattern.match(stripped) for pattern in NOISE_PATTERNS):
            continue

        kept_lines.append(stripped)

    return "\n".join(kept_lines)


def load_and_clean_documents(directory=DOCUMENTS_DIR):
    """Load every .txt file in `directory`, clean it, and return a list of
    (filename, cleaned_text) tuples. Files that end up empty after cleaning
    are skipped.
    """
    documents = []

    # Sort for deterministic, repeatable ordering across runs.
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".txt"):
            continue

        file_path = os.path.join(directory, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        cleaned = clean_text(raw_text)

        # Only keep files that still have content after cleaning.
        if cleaned.strip():
            documents.append((filename, cleaned))

    return documents


# ---------------------------------------------------------------------------
# Step 2: Chunking strategy
# ---------------------------------------------------------------------------

# Markdown headers used by structured documents (e.g. the Good/Bad/Ugly review
# roundup). `#` marks a category, `##` marks an individual apartment/section.
HEADERS_TO_SPLIT_ON = [
    ("#", "category"),
    ("##", "apartment"),
]


def _context_prefix(metadata):
    """Build a short context line to prepend to a chunk's text.

    The point is that EVERY chunk should name what it is about, even tail
    chunks of a long review that no longer contain the apartment name. We
    derive that context from the metadata captured during splitting.
    """
    apartment = metadata.get("apartment")
    category = metadata.get("category")

    if apartment:
        # e.g. "[The Domain — The Ugly]"
        return f"[{apartment} — {category}]" if category else f"[{apartment}]"
    if category:
        return f"[{category}]"
    # Unstructured docs (single-topic threads): fall back to the post title.
    title = metadata.get("title")
    return f"[{title}]" if title else None


def chunk_documents(documents):
    """Split each (filename, cleaned_text) pair into overlapping chunks.

    Two-stage strategy:
      1. If a document contains Markdown headers, first split on them so the
         category/apartment name is captured as metadata for the whole section.
      2. Then size-split every section with RecursiveCharacterTextSplitter
         (500 chars / 100 overlap), which inherits that metadata.

    Finally a context prefix (e.g. "[The Domain — The Ugly]") is prepended to
    each chunk's text so no chunk is orphaned from the apartment it describes.

    Each returned chunk is a Document whose metadata links it back to its
    source file, e.g. {"source": "Gameday Parking.txt"}.
    """
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        # Measure length in raw characters, matching the spec's "characters".
        length_function=len,
    )
    # strip_headers=True keeps the header text out of the body — we re-add it
    # ourselves, uniformly, as the context prefix below.
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS_TO_SPLIT_ON,
        strip_headers=True,
    )

    all_chunks = []
    for filename, text in documents:
        # The first line of a cleaned file is its post title; use it as
        # fallback context for unstructured (single-topic) documents.
        title = text.splitlines()[0].strip() if text.strip() else filename

        if "\n#" in "\n" + text:
            # Structured document: split by header first, then by size.
            sections = header_splitter.split_text(text)
            chunks = char_splitter.split_documents(sections)
        else:
            # Single-topic thread: straight size split.
            chunks = char_splitter.create_documents(texts=[text])

        for chunk in chunks:
            chunk.metadata["source"] = filename
            chunk.metadata.setdefault("title", title)
            prefix = _context_prefix(chunk.metadata)
            if prefix:
                chunk.page_content = f"{prefix}\n{chunk.page_content}"
            all_chunks.append(chunk)

    return all_chunks


def ingest(directory=DOCUMENTS_DIR):
    """Full pipeline: load + clean + chunk. Returns the list of chunks."""
    documents = load_and_clean_documents(directory)
    return chunk_documents(documents)


# ---------------------------------------------------------------------------
# Step 3: Verification test script
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    chunks = ingest()

    print("=" * 70)
    print(f"Total chunks generated across all documents: {len(chunks)}")
    print("=" * 70)

    # Randomly sample up to 5 chunks for visual inspection of formatting.
    sample_size = min(5, len(chunks))
    sample = random.sample(chunks, sample_size)

    print(f"\nShowing {sample_size} random chunks:\n")
    for i, chunk in enumerate(sample, start=1):
        print(f"--- Chunk {i} ---")
        print(f"Source   : {chunk.metadata.get('source')}")
        # Show the structured context captured during splitting, when present.
        if chunk.metadata.get("apartment"):
            print(f"Apartment: {chunk.metadata.get('apartment')}")
        if chunk.metadata.get("category"):
            print(f"Category : {chunk.metadata.get('category')}")
        print(f"Length   : {len(chunk.page_content)} chars")
        print("Text     :")
        print(chunk.page_content)
        print()
