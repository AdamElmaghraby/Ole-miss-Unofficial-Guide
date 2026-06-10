"""
generate.py — Milestone 5 (backend): grounded LLM generation.

This module wires the retrieval half (from ingest.py) to a Groq-hosted LLM:

    user query
      -> retrieve_documents(query, top_k=4)        # semantic search (ingest.py)
      -> build a context string from the chunks
      -> Groq chat completion with a strict grounding system prompt
      -> programmatically append the cited source filenames

The LLM is told to answer using ONLY the retrieved context, and to refuse
outright when the answer isn't present — so it never falls back on outside
knowledge.

Prerequisites:
  - Run `python ingest.py` once first to build the ./chroma_db vector store.
  - Put your Groq key in a local .env file:  GROQ_API_KEY=gsk_...
  - pip install groq python-dotenv
"""

import os

from dotenv import load_dotenv
from groq import Groq

# Reuse the Milestone 4 retrieval function — single source of truth.
from ingest import retrieve_documents

# Load GROQ_API_KEY (and anything else) from a local .env file.
load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GROQ_MODEL = "llama-3.3-70b-versatile"
TOP_K = 4

# The exact sentence the model must return when the context can't answer the
# question. Kept as a constant so we can detect a refusal afterwards.
REFUSAL_MESSAGE = (
    "I'm sorry, but that information isn't available in the student reviews "
    "and parking logs."
)

# Airtight grounding instructions. The model gets ONLY what's in the context.
SYSTEM_PROMPT = f"""You are an AI assistant that helps a student navigate \
off-campus housing and commuting at the University of Mississippi (Ole Miss) \
in Oxford, MS. Your knowledge comes from a set of student reviews and parking \
discussions that will be provided to you as context.

Follow these rules with no exceptions:
1. Answer the user's question using ONLY the information in the provided \
context chunks. Do not use any outside, general, or prior knowledge.
2. If the answer cannot be found completely within the provided context, you \
must reply with EXACTLY this sentence and nothing else:
"{REFUSAL_MESSAGE}"
3. Never invent or guess apartment names, prices, times, rules, or facts that \
are not explicitly stated in the context.
4. Do not write out, list, or mention the source file names yourself — the \
system appends sources separately.
5. Keep the answer concise and directly grounded in what the students said."""


# ---------------------------------------------------------------------------
# Groq client (lazy + cached)
# ---------------------------------------------------------------------------

_client = None


def get_groq_client():
    """Return a cached Groq client, reading the key securely from the env."""
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to your .env file "
                "(GROQ_API_KEY=gsk_...) before running generation."
            )
        _client = Groq(api_key=api_key)
    return _client


# ---------------------------------------------------------------------------
# Generation pipeline
# ---------------------------------------------------------------------------

def _build_context(chunks):
    """Combine retrieved chunks into a single labeled context string."""
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        source = chunk["metadata"].get("source", "unknown")
        blocks.append(f"[Chunk {i} | source: {source}]\n{chunk['text']}")
    return "\n\n".join(blocks)


def _unique_sources(chunks):
    """Extract unique source filenames, preserving retrieval order."""
    sources = []
    for chunk in chunks:
        source = chunk["metadata"].get("source")
        if source and source not in sources:
            sources.append(source)
    return sources


def _is_refusal(answer):
    """True if the model declined to answer (context didn't cover the query)."""
    # Match on the distinctive tail so minor punctuation/whitespace differences
    # from the model don't break detection.
    return "isn't available in the student reviews and parking logs" in answer.lower()


def generate_response(query, top_k=TOP_K):
    """Run the full RAG generation loop for a single query.

    1. Retrieve the top_k most relevant chunks.
    2. Build a grounded context string from them.
    3. Ask the Groq LLM to answer using only that context.
    4. Append the cited source filenames (only when the model actually
       answered — we don't cite sources behind a refusal).
    """
    # 1. Retrieve relevant context via Milestone 4's semantic search.
    chunks = retrieve_documents(query, top_k=top_k)
    context = _build_context(chunks)

    # 2 & 3. Ask the LLM, constraining it to the retrieved context.
    client = get_groq_client()
    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Context:\n{context}\n\n"
                    f"Question: {query}"
                ),
            },
        ],
        # Deterministic + grounded: no creative temperature.
        temperature=0.0,
    )
    answer = completion.choices[0].message.content.strip()

    # 4. Programmatically append sources — but not behind a refusal, since the
    #    retrieved chunks didn't actually support an answer in that case.
    if _is_refusal(answer):
        return answer

    sources = _unique_sources(chunks)
    if sources:
        source_block = "Unverified Student Sources Cited:\n" + "\n".join(
            f"- {source}" for source in sources
        )
        return f"{answer}\n\n{source_block}"
    return answer


# ---------------------------------------------------------------------------
# Verification test block
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        ("In-Scope", "What do tenants say about the maintenance at the Azul?"),
        ("Out-of-Scope", "What is the capital of France?"),
    ]

    for label, query in tests:
        print("=" * 70)
        print(f"[{label}] Query: {query}")
        print("=" * 70)
        print(generate_response(query))
        print()
