"""
ingest.py — Milestones 3 & 4: Ingestion, Chunking, Embedding & Retrieval.

This script:
  1. Loads every .txt file in the documents/ directory.
  2. Cleans out common Reddit UI noise line-by-line and drops empty lines.
  3. Splits the cleaned text into overlapping chunks with LangChain's
     RecursiveCharacterTextSplitter (size=500, overlap=100).
  4. Attaches the source filename as metadata to every chunk.
  5. Embeds the chunks with SentenceTransformer('all-MiniLM-L6-v2') and stores
     them in a local, on-disk ChromaDB collection (./chroma_db).
  6. Exposes retrieve_documents(query, top_k=4) for semantic search.

Run directly (`python ingest.py`) to execute the verification block at the
bottom: it ingests + embeds everything, then runs a sample retrieval query.

Requires: pip install langchain-text-splitters sentence-transformers chromadb
"""

import os
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

# --- Embedding & vector store (Milestone 4) -------------------------------
# Sentence-Transformers model used to embed both chunks and queries. It must be
# the SAME model for storage and retrieval so the vectors live in one space.
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

# On-disk ChromaDB location, resolved next to this script so the persisted
# vectors are saved regardless of the working directory.
CHROMA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db")
COLLECTION_NAME = "olemiss_guide"

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
# Step 3: Embedding & vector storage (Milestone 4)
# ---------------------------------------------------------------------------

# The embedding model is heavy to construct, so we load it once and reuse it
# across both storage and retrieval.
_embedding_model = None


def get_embedding_model():
    """Return a cached SentenceTransformer('all-MiniLM-L6-v2') instance."""
    global _embedding_model
    if _embedding_model is None:
        # Imported lazily so chunking alone doesn't require the heavy deps.
        from sentence_transformers import SentenceTransformer

        _embedding_model = SentenceTransformer(EMBED_MODEL_NAME)
    return _embedding_model


def _clean_metadata(metadata):
    """ChromaDB metadata values must be str/int/float/bool — drop None values.

    Single-topic threads have no apartment/category, so those keys are None and
    must be removed before they're handed to Chroma.
    """
    return {key: value for key, value in metadata.items() if value is not None}


def embed_and_store(chunks, persist_dir=CHROMA_DIR, collection_name=COLLECTION_NAME):
    """Embed chunks and persist them to an on-disk ChromaDB collection.

    The collection is recreated from scratch on every run so re-ingesting never
    duplicates vectors. Each vector keeps its source filename (plus apartment /
    category / title when available) as metadata.

    Returns the populated Chroma collection.
    """
    import chromadb

    model = get_embedding_model()

    texts = [chunk.page_content for chunk in chunks]
    metadatas = [_clean_metadata(chunk.metadata) for chunk in chunks]
    # Stable, unique id per chunk: "<source>::<index>".
    ids = [
        f"{chunk.metadata.get('source', 'doc')}::{i}"
        for i, chunk in enumerate(chunks)
    ]

    # Embed every chunk (returns a numpy array; Chroma wants plain lists).
    embeddings = model.encode(texts, show_progress_bar=False).tolist()

    # PersistentClient writes the vectors to disk at persist_dir.
    client = chromadb.PersistentClient(path=persist_dir)
    # Start clean: drop any existing collection of the same name.
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass
    collection = client.create_collection(
        name=collection_name,
        # Cosine distance is the natural fit for sentence-transformer vectors
        # (0 = identical, larger = less similar).
        metadata={"hnsw:space": "cosine"},
    )

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )
    return collection


# ---------------------------------------------------------------------------
# Step 4: Retrieval
# ---------------------------------------------------------------------------

def retrieve_documents(query, top_k=4, persist_dir=CHROMA_DIR, collection_name=COLLECTION_NAME):
    """Semantic search over the persisted ChromaDB collection.

    Loads the on-disk collection (independent of any in-memory state), embeds
    `query` with the same model used for storage, and returns the top_k most
    similar chunks.

    Returns a list of dicts: {"text", "metadata", "distance"}, ordered from
    most to least similar (smallest cosine distance first).
    """
    import chromadb

    model = get_embedding_model()
    query_embedding = model.encode([query]).tolist()

    client = chromadb.PersistentClient(path=persist_dir)
    collection = client.get_collection(collection_name)

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
    )

    # Chroma nests results one level per query; we sent a single query.
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    return [
        {"text": text, "metadata": metadata, "distance": distance}
        for text, metadata, distance in zip(documents, metadatas, distances)
    ]


# ---------------------------------------------------------------------------
# Step 5: Verification test script
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # 1. Ingest + chunk every document.
    chunks = ingest()
    print("=" * 70)
    print(f"Total chunks generated across all documents: {len(chunks)}")

    # 2. Embed the chunks and persist them to ./chroma_db.
    print(f"Embedding chunks with '{EMBED_MODEL_NAME}' and storing in {CHROMA_DIR} ...")
    embed_and_store(chunks)
    print(f"Stored {len(chunks)} vectors in ChromaDB collection '{COLLECTION_NAME}'.")
    print("=" * 70)

    # 3. Run the 5 evaluation questions from planning.md (the Evaluation Plan
    #    table). Each tuple is (question, expected answer) so retrieval quality
    #    can be judged against the documented ground truth.
    eval_questions = [
        (
            "What do tenants say about the maintenance at the Azul?",
            "The maintenance at Azul does not respond or care for tenants.",
        ),
        (
            "What time do campus commuter parking lots typically fill up to "
            "capacity in the morning?",
            "Students state that commuter parking lots consistently fill up "
            "completely between 9:00 AM and 10:00 AM.",
        ),
        (
            "What are the unwritten rules for parking in faculty or restricted "
            "zones after 5:00 PM?",
            "Zone enforcement loosens from 5:00 PM to 7:00 AM, allowing students "
            "to park in most standard zones, provided the spot is not marked as "
            "24/7 reserved or handicapped.",
        ),
        (
            "What is the general student consensus regarding living at Northgate "
            "Apartments?",
            "It is viewed as a convenient, affordable on-campus housing option "
            "for upperclassmen or graduate students, though the facilities are "
            "older.",
        ),
        (
            "How do off-campus students living in local complexes utilize the "
            "OUT bus transit system to handle parking issues?",
            "Students leverage the apartment complex shuttle loops / OUT bus to "
            "ride directly to campus, bypassing the need for a commuter parking "
            "pass.",
        ),
    ]

    for q_num, (question, expected) in enumerate(eval_questions, start=1):
        print("\n" + "#" * 70)
        print(f"Q{q_num}: {question}")
        print(f"Expected: {expected}")
        print("#" * 70)

        results = retrieve_documents(question, top_k=4)
        print(f"Top {len(results)} retrieved chunks:\n")
        for rank, result in enumerate(results, start=1):
            metadata = result["metadata"]
            print(f"--- Result {rank} ---")
            print(f"Source   : {metadata.get('source')}")
            if metadata.get("apartment"):
                print(f"Apartment: {metadata.get('apartment')}")
            if metadata.get("category"):
                print(f"Category : {metadata.get('category')}")
            # Lower cosine distance == more semantically similar.
            print(f"Distance : {result['distance']:.4f}")
            print("Text     :")
            print(result["text"])
            print()
