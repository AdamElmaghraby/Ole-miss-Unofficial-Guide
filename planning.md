# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

I chose the domain The Oxford Off-Campus Housing & Commuting Reality Check, which captures student-generated lore regarding local apartment conditions, hidden leasing fees, and unwritten campus parking lot fill-up times. This knowledge is incredibly valuable for navigating daily logistics safely and avoiding costly citations, yet it remains completely absent from official, marketing-driven university and property management websites.

---

## Documents

| #   | Source           | Description                                                                                                                 | URL or location                                                                                       |
| --- | ---------------- | --------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| 1   | r/olemiss Thread | Comprehensive student reviews of specific Oxford apartment complexes detailing the good, the bad, and the ugly.             | `https://www.reddit.com/r/olemiss/comments/1ftqigl/looking_for_apartments_in_oxford_ms_the_good_the/` |
| 2   | r/olemiss Thread | Student recommendations, hidden fees, and warnings regarding budget-friendly housing options near campus.                   | `https://www.reddit.com/r/olemiss/comments/171g7lp/cheap_oxford_apartments_near_olemiss/`             |
| 3   | r/olemiss Thread | General peer advice and consolidated recommendations for finding reliable apartment complexes in town.                      | `https://www.reddit.com/r/olemiss/comments/f33vv7/apartment_complex_recommendations/`                 |
| 4   | r/olemiss Thread | Highly specific, critical review outlining severe management and maintenance warnings at Azul Apartments.                   | `https://www.reddit.com/r/olemiss/comments/1ft6hbz/avoid_azul_apartments_in_oxford_at_all_costs/`     |
| 5   | r/olemiss Thread | Insights and realities of living at Northgate Apartments, focusing on on-campus upperclassmen and grad housing.             | `https://www.reddit.com/r/olemiss/comments/1t1q61t/northgate_apartments/`                             |
| 6   | r/olemiss Thread | Unofficial student observations detailing exactly what time specific morning commuter parking lots fill to capacity.        | `https://www.reddit.com/r/olemiss/comments/1t0elp2/parking_on_campus/`                                |
| 7   | r/olemiss Thread | Survival guide covering strict parking enforcement, the realities of the Commuter Red pass, and the OUT bus transit system. | `https://www.reddit.com/r/olemiss/comments/1n2p7f7/parking/`                                          |
| 8   | r/olemiss Thread | Clarification of the unwritten rules and realities of parking in faculty/restricted zones between 5 PM and 7 AM.            | `https://www.reddit.com/r/olemiss/comments/1f21o0d/parking_after_5/`                                  |
| 9   | r/olemiss Thread | Student workarounds, secret spots, and advice for navigating visitor parking and temporary passes on campus.                | `https://www.reddit.com/r/olemiss/comments/1dz35ug/where_is_a_good_place_to_park/`                    |
| 10  | r/olemiss Thread | Local Oxford strategies for game day parking, including utilizing off-campus shuttles and navigating paid local lots.       | `https://www.reddit.com/r/olemiss/comments/1owxytm/gameday_parking/`                                  |

---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:500 characters**

**Overlap:100 characters**

**Reasoning:Since the corpus consists entirely of Reddit threads, the text structure is made up of short, dense, and highly opinionated comments rather than long-form articles. A 500-character chunk perfectly captures a standard 3-to-4 sentence Reddit comment. This keeps a complete thought.**

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:all-MiniLM-L6-v2**

**Top-k:4 chunks**

\*\*Production tradeoff reflection:

1. Context Length vs. Document Integrity:
   Our local model restricts text inputs to a strict limit of 256 tokens per chunk, which forces us to cut student discussions into smaller fragments. Production-tier enterprise models (such as OpenAI's text-embedding-3-large or Cohere's embed-english-v3.0) support massive input boundaries up to 8,192 tokens. Upgrading would allow us to scale up our chunk sizes significantly, preserving the complete structural and conversational flow of entire multi-paragraph Reddit threads as a single unified vector.

2. Embedding Dimensionality vs. Operational Cost:
   The 384-dimensional space of our current model captures broad semantic meanings but misses finer details. Premium commercial models expand this capacity to 1,536 or 3,072 dimensions. This expansion vastly improves retrieval accuracy for highly specific student queries—such as distinguishing between a "Commuter Red" or "Commuter Blue" lot restriction. However, storing higher-dimensional vectors exponentially increases RAM and disk usage within the vector database, driving up infrastructure hosting costs.

3. Domain-Specific Language and Slang:
   Standard off-the-shelf embedding models are trained on general internet text (like Wikipedia) and naturally struggle with hyper-local college jargon or student slang (e.g., "The Velvet Ditch," "The Grove," "OUT bus," or "Commuter Red"). In a production roll-out, we would weigh the high API cost of general commercial models against the engineering overhead of fine-tuning a smaller open-source model directly on local student forum data to map regional terminology accurately.

4. Latency vs. Network Dependencies:
   Running embeddings locally means our vector database handles searches almost instantaneously. Moving to a cloud-hosted API introduces network overhead on every single user search, adding latency and exposing our app to third-party rate limits or unexpected downtime. A production strategy would have to balance the superior accuracy of cloud embeddings against the snappy, reliable performance of an internally hosted model.
   \*\*

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| #   | Question                                                                                                          | Expected answer                                                                                                                                                                           |
| --- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | What do tenants say about the maintnence at the Azul                                                              | The maintence at azul does not respond or care for tenants.                                                                                                                               |
| 2   | What time do campus commuter parking lots typically fill up to capacity in the morning?                           | Students state that commuter parking lots consistently fill up completely between 9:00 AM and 10:00 AM.                                                                                   |
| 3   | What are the unwritten rules for parking in faculty or restricted zones after 5:00 PM?                            | Zone enforcement loosens from 5:00 PM to 7:00 AM, allowing students to park in most standard zones, provided the spot is not marked as 24/7 reserved or handicapped.                      |
| 4   | What is the general student consensus regarding living at Northgate Apartments?                                   | It is viewed as a highly convenient, affordable on-campus housing option tailored for upperclassmen or graduate students, though the facilities are older.                                |
| 5   | How do off-campus students living in local complexes utilize the OUT bus transit system to handle parking issues? | Students leverage the mandatory apartment complex shuttle loops to ride the OUT bus directly to campus, completely bypassing the need to buy or find a spot with a commuter parking pass. |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1. Conflicting opinions or statements in the sources.

2. Lack of information on query'd question, could cause halucination.

---

## Architecture

```
mermaid
graph TD
    %% Milestone 3: Ingestion & Chunking
    subgraph Ingestion_and_Chunking [Milestone 3: Ingestion & Chunking]
        A[Raw Reddit Threads] -->|Manually Saved| B[Local .txt Files]
        B -->|Python File Reader| C[Raw Text Strings]
        C -->|LangChain RecursiveCharacterTextSplitter| D[Text Chunks<br/>Size: 500 char | Overlap: 100 char]
    end

    %% Milestone 4: Embedding & Retrieval
    subgraph Embedding_and_Retrieval [Milestone 4: Embedding & Vector Store]
        D -->|sentence-transformers<br/>all-MiniLM-L6-v2| E[384-Dim Vectors]
        E -->|Index & Persist| F[(Local ChromaDB)]
    end

    %% Milestone 5: Generation & Interface
    subgraph Generation_and_Interface [Milestone 5: Retrieval, Generation & UI]
        G[Gradio UI User Query] -->|Embed Query| H[Query Vector]
        H -->|Vector Search<br/>Top-k: 4| F
        F -->|Retrieve Context Chunks| I[Augmented Prompt Template]
        G -->|Pass Original Query| I
        I -->|API Payload| J[Groq API<br/>llama-3.3-70b-versatile]
        J -->|Generated Response| K[Gradio UI Output]
    end

    %% Styling Elements
    style F fill:#2a2a3a,stroke:#4f46e5,stroke-width:2px;
    style J fill:#1e293b,stroke:#06b6d4,stroke-width:2px;
    style G fill:#1c2d1c,stroke:#22c55e,stroke-width:2px;
    style K fill:#1c2d1c,stroke:#22c55e,stroke-width:2px;
```

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:**

- **Tool:** Claude
- **Input:** The Documents list, the Chunking Strategy (500 char limit, 100 char overlap), and the Architecture diagram. I will instruct it to use LangChain's `RecursiveCharacterTextSplitter` to process 10 local `.txt` files.
- **Expected Output:** A Python script that loads the `.txt` files, cleans the raw text, and generates the text chunks with attached source metadata.
- **Verification:** I will ask Claude to generate a simple Python test script that prints the total number of chunks created and outputs 5 random chunks to the terminal so I can visually confirm they are readable, self-contained, and respect the overlap rule.

**Milestone 4 — Embedding and retrieval:**

- **Tool:** Claude
- **Input:** The Retrieval Approach section, specifying the use of `sentence-transformers` (`all-MiniLM-L6-v2`) and a local ChromaDB instance with a `top-k` of 4.
- **Expected Output:** Python code that takes the chunks from Milestone 3, embeds them, saves them into a local ChromaDB collection, and includes a retrieval function that accepts a user query.
- **Verification:** I will run a test script passing 3 of my evaluation questions into the retrieval function. I will print the retrieved chunks and their distance scores to ensure the content is actually relevant to the queries before moving on to the LLM step.

**Milestone 5 — Generation and interface:**

- **Tool:** Claude
- **Input:** The requirement to use Groq's `llama-3.3-70b-versatile` API, the grounding instruction (answers must rely _only_ on retrieved context and cite sources), and the request for a Gradio web interface.
- **Expected Output:** An `app.py` script that wires the retrieval function to the Groq LLM using a strictly grounded system prompt, wrapped in a basic Gradio UI with input/output text boxes.
- **Verification:** I will launch the Gradio app locally and test it with an out-of-scope question (e.g., "What is the capital of France?"). The system passes verification if it explicitly refuses to answer rather than hallucinating a response from its general training data.
