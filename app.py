"""
app.py — Milestone 5: Gradio web UI for the RAG assistant.

This is the thin presentation layer. All the real work lives in:
  - ingest.py    : retrieval (semantic search over ChromaDB)
  - generate.py  : grounded generation via the Groq LLM

This file just wires generate_response() to a web interface.

--------------------------------------------------------------------------
HOW TO RUN
--------------------------------------------------------------------------
  1. One-time setup (build the vector store):   python ingest.py
  2. Make sure your Groq key is in .env:        GROQ_API_KEY=gsk_...
  3. Launch the web app:                        python app.py
  4. Open the local URL it prints (default http://127.0.0.1:7860).

Requires: pip install gradio groq python-dotenv  (plus the ingest deps)
"""

import gradio as gr
from dotenv import load_dotenv

# Load environment variables (GROQ_API_KEY) BEFORE importing the generation
# module, so the Groq client can initialize smoothly when the server starts.
# (generate.py also calls load_dotenv(); calling it here too is harmless and
# makes the dependency explicit.)
load_dotenv()

from generate import generate_response


# ---------------------------------------------------------------------------
# UI <-> backend bridge
# ---------------------------------------------------------------------------

def answer_question(query):
    """Call the RAG backend and return a string for the output textbox.

    Any failure (Groq API error, missing ChromaDB store, etc.) is caught and
    returned as a readable message so the web server never crashes.
    """
    if not query or not query.strip():
        return "Please enter a question to get started."

    try:
        return generate_response(query)
    except Exception as exc:  # noqa: BLE001 - surface any backend failure in the UI
        # Common causes: missing GROQ_API_KEY, no ./chroma_db (run ingest.py),
        # network/API errors. Show it instead of letting the server fall over.
        return (
            "⚠️ Something went wrong while answering your question.\n\n"
            f"Error: {exc}\n\n"
            "Tips: make sure GROQ_API_KEY is set in your .env file and that "
            "you've run `python ingest.py` to build the ./chroma_db store."
        )


# Evaluation-plan questions, surfaced as one-click examples.
EXAMPLE_QUESTIONS = [
    "What do tenants say about the maintenance at the Azul?",
    "What time do campus commuter parking lots typically fill up to capacity in the morning?",
    "What are the unwritten rules for parking in faculty or restricted zones after 5:00 PM?",
]


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

def build_demo():
    """Build and return the Gradio Blocks interface."""
    # Note: in Gradio 6 the `theme` is passed to launch(), not the Blocks ctor.
    with gr.Blocks(
        title="The Oxford Off-Campus Housing & Commuting Reality Check",
    ) as demo:
        # Title + subtitle.
        gr.Markdown("# The Oxford Off-Campus Housing & Commuting Reality Check")
        gr.Markdown(
            "An unofficial, student-grounded RAG assistant for navigating "
            "local apartment conditions, hidden fees, and campus parking "
            "realities."
        )

        with gr.Row():
            with gr.Column(scale=1):
                query_box = gr.Textbox(
                    label="Your question",
                    placeholder="e.g. Which apartments have the worst maintenance?",
                    lines=4,
                )
                with gr.Row():
                    # ClearButton wipes the listed components in one click.
                    clear_btn = gr.ClearButton(
                        components=[query_box],
                        value="Clear",
                    )
                    submit_btn = gr.Button("Submit", variant="primary")

            with gr.Column(scale=1):
                output_box = gr.Textbox(
                    label="Answer (grounded in student reviews & parking logs)",
                    lines=14,
                )

        # Clear should reset the answer too.
        clear_btn.add(output_box)

        # One-click examples: clicking fills the question AND runs it live
        # (run_on_click=True). cache_examples=False avoids calling the LLM at
        # startup, so the server boots without spending API calls.
        gr.Examples(
            examples=EXAMPLE_QUESTIONS,
            inputs=query_box,
            outputs=output_box,
            fn=answer_question,
            run_on_click=True,
            cache_examples=False,
            label="Try an example (from our evaluation plan)",
        )

        # Wire up Submit button and the Enter key in the textbox.
        submit_btn.click(fn=answer_question, inputs=query_box, outputs=output_box)
        query_box.submit(fn=answer_question, inputs=query_box, outputs=output_box)

    return demo


if __name__ == "__main__":
    demo = build_demo()
    # share=False keeps it local-only. Set share=True to get a temporary
    # public Gradio link (e.g. for a quick demo to others):
    #   demo.launch(share=True, theme=gr.themes.Soft())
    demo.launch(share=False, theme=gr.themes.Soft())
