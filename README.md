# The Unofficial Guide — Project 1

The Oxford Off-Campus Housing & Commuting Reality Check — an unofficial,
student-grounded RAG assistant for navigating local apartment conditions,
hidden fees, and campus parking realities at the University of Mississippi.

---

## Domain

The Oxford/Ole Miss Off-Campus Housing & Commuting Reality Check.
This is useful because of the competitive housing market for Ole Miss students; it will equip upcoming students with the knowledge they need to make the best decision for their stay in Oxford. This knowledge is crucial for students but is entirely absent from the official Ole Miss housing and transit websites.

---

## Document Sources

| # | Source | Type | URL or file path |
| --- | --- | --- | --- |
| 1 | r/olemiss - Looking for Apartments In Oxford MS - The Good The Bad, and The Ugly | Reddit Thread | https://www.reddit.com/r/olemiss/comments/1ftqigl/looking_for_apartments_in_oxford_ms_the_good_the/ |
| 2 | r/olemiss - cheap Oxford Apartments near OleMiss | Reddit Thread | https://www.reddit.com/r/olemiss/comments/171g7lp/cheap_oxford_apartments_near_olemiss/ |
| 3 | r/olemiss - apartment complex recommendations | Reddit Thread | https://www.reddit.com/r/olemiss/comments/f33vv7/apartment_complex_recommendations/ |
| 4 | r/olemiss - Avoid Azul Apartments In Oxford at all Costs | Reddit Thread | https://www.reddit.com/r/olemiss/comments/1ft6hbz/avoid_azul_apartments_in_oxford_at_all_costs/ |
| 5 | r/olemiss - Northgate Apartments? (On-campus upperclassmen/grad housing) | Reddit Thread | https://www.reddit.com/r/olemiss/comments/1t1q61t/northgate_apartments/ |
| 6 | r/olemiss - Parking on campus? (Morning lot fill-up times) | Reddit Thread | https://www.reddit.com/r/olemiss/comments/1t0elp2/parking_on_campus/ |
| 7 | r/olemiss - Parking (Strict enforcement, Commuter Red passes, and OUT bus) | Reddit Thread | https://www.reddit.com/r/olemiss/comments/1n2p7f7/parking/ |
| 8 | r/olemiss - Parking after 5 (Unwritten 5 PM to 7 AM zone rules) | Reddit Thread | https://www.reddit.com/r/olemiss/comments/1f21o0d/parking_after_5/ |
| 9 | r/olemiss - Where is a good place to park? (Visitor parking & temporary passes) | Reddit Thread | https://www.reddit.com/r/olemiss/comments/1dz35ug/where_is_a_good_place_to_park/ |
| 10 | r/olemiss - Gameday Parking (Shuttles, Jackson Avenue Center, and paid local lots) | Reddit Thread | https://www.reddit.com/r/olemiss/comments/1owxytm/gameday_parking/ |

---

## Chunking Strategy

**Chunk size:** 500 characters

**Overlap:** 100 characters

**Why these choices fit your documents:**
The corpus is made entirely of Reddit threads — short, dense, opinionated comments rather than long-form articles. A 500-character window comfortably holds a typical 3–4 sentence Reddit comment, so a single chunk usually captures one complete thought (one tenant's review, one parking tip). The 100-character overlap (20%) carries a sentence or two across each boundary so a thought that spans a split isn't cleanly severed.

**Preprocessing before chunking:**
The raw `.txt` files were copy-pasted Reddit pages full of UI noise (nav chrome, "Sign Up / Log In," upvote counts, `•`/timestamp lines, the "People also ask" sidebar, related-post spam, and the legal footer). I cleaned these out — both with a programmatic line-level filter (keyword + exact-match + regex tiers in `ingest.py`) and by hand-editing the source files down to just the real post + comments. One document, *The Good The Bad, and The Ugly*, is a structured review roundup where each apartment is its own section. For that file I added Markdown headers (`#` category like "The Bad," `##` apartment name) and use a two-stage split: `MarkdownHeaderTextSplitter` captures the apartment/category into metadata, then `RecursiveCharacterTextSplitter` (500/100) splits within each section. A short context prefix (e.g. `[The Domain — The Ugly]`) is prepended to every chunk so even a tail chunk of a long review still names the apartment it describes.

**Final chunk count:** 126 chunks across all 10 documents.

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` (via `sentence-transformers`), producing 384-dimensional vectors stored in a local, on-disk ChromaDB collection (`./chroma_db`) using cosine distance. The same model embeds both the stored chunks and the user's query at retrieval time. Top-k = 4.

**Production tradeoff reflection:**
`all-MiniLM-L6-v2` was chosen because it is small (~80 MB), runs locally and offline, is free, and returns results near-instantly — ideal for a class project. If deploying for real users with cost off the table, I'd weigh several upgrades:

- **Context length vs. document integrity.** This model truncates inputs at ~256 tokens, forcing student discussions into small fragments. Enterprise models (OpenAI `text-embedding-3-large`, Cohere `embed-english-v3.0`) accept up to 8,192 tokens, letting me embed entire multi-paragraph threads as single coherent vectors.
- **Dimensionality vs. cost.** 384 dimensions capture broad meaning but miss fine distinctions (e.g. "Commuter Red" vs. "Commuter Blue"). Premium models use 1,536–3,072 dims for sharper retrieval, but higher-dimensional vectors cost more RAM/disk in the vector store.
- **Domain slang.** Off-the-shelf models are trained on general web text and stumble on hyper-local jargon ("The Velvet Ditch," "OUT bus," "Commuter Red"). In production I'd weigh API cost against fine-tuning a smaller open model on local student-forum data to map this terminology. (This limitation directly caused my failure case — see below.)
- **Latency vs. network dependency.** Local embedding is instant and reliable; a cloud API adds per-query network latency and exposes the app to third-party rate limits and downtime.

---

## Grounded Generation

The generation backend (`generate.py`) uses Groq's `llama-3.3-70b-versatile` at `temperature=0.0` (deterministic, anti-hallucination).

**System prompt grounding instruction:**
The model is told it is an assistant for Ole Miss off-campus housing/commuting whose knowledge comes *only* from the provided context chunks. The key rules:
1. Answer using ONLY the provided context — no outside, general, or prior knowledge.
2. If the answer cannot be found completely within the context, reply with EXACTLY:
   *"I'm sorry, but that information isn't available in the student reviews and parking logs."*
3. Never invent apartment names, prices, times, or rules not explicitly in the context.
4. Do not write out source names — the system appends those separately.

Structurally, grounding is reinforced by (a) retrieving only the top-4 chunks and formatting them as a labeled `Context:` block in the user message, and (b) the deterministic temperature, so the model can't drift creatively. The out-of-scope test ("What is the capital of France?") returns the exact refusal sentence, confirming the model does not fall back on training knowledge.

**How source attribution is surfaced in the response:**
The LLM is explicitly forbidden from naming sources. Instead, `generate_response()` extracts the unique `source` filenames from the retrieved chunks' metadata and programmatically appends an `Unverified Student Sources Cited:` block to the end of the answer. This block is deliberately **skipped when the model refuses**, so a refusal never cites sources that didn't actually support an answer.

---

## Evaluation Report

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | What do tenants say about the maintenance at the Azul? | Maintenance at Azul does not respond or care for tenants. | "24-hr Maintenance is a joke," ~24-hour response times; plumbing/mold/holes/walls "painted over" rather than repaired. Cites *Avoid Azul Apartments…*. | Relevant | **Accurate** |
| 2 | What time do campus commuter parking lots typically fill up to capacity in the morning? | Lots consistently fill between 9:00–10:00 AM. | "Commuter red lots are full to the max by 9 am, and most parking lots fill up between 9 and 10 a.m." | Relevant | **Accurate** |
| 3 | What are the unwritten rules for parking in faculty/restricted zones after 5:00 PM? | Enforcement loosens 5 PM–7 AM; park most standard zones unless 24/7 reserved or handicapped. | "Park in any zone, including faculty, from 5pm–7am, unless timed/handicap/reserved 24/7. Weekends not enforced." | Relevant | **Accurate** |
| 4 | What is the general student consensus regarding living at Northgate Apartments? | Convenient, affordable on-campus housing for upperclassmen/grad students, though facilities are older. | Reports the consensus is **mixed**: one calls them "gross"/cheap-housing, another corrects that they were grad/upperclassmen housing, a third says "they are fine lol." | Relevant | **Partially accurate** |
| 5 | How do off-campus students use the OUT bus transit system to handle parking issues? | Students use complex shuttle loops / the OUT bus to ride to campus, bypassing the need for a commuter parking pass. | **Refused:** "I'm sorry, but that information isn't available in the student reviews and parking logs." | Partially relevant | **Inaccurate** |

**Retrieval quality:** Relevant / Partially relevant / Off-target
**Response accuracy:** Accurate / Partially accurate / Inaccurate

**Notes on the partial (Q4):** The system was *faithful to the source* — the actual Northgate thread is short and genuinely conflicted, so the honest summary is "mixed," not the tidy "convenient and affordable" framing the expected answer assumed. The expected answer was slightly more optimistic than what students actually wrote. I count this as partially accurate: it correctly surfaced the upperclassmen/grad-housing and "older facilities" angle but did not (and arguably should not) declare a positive consensus the documents don't support.

---

## Failure Case Analysis

**Question that failed:** Q5 — "How do off-campus students living in local complexes utilize the OUT bus transit system to handle parking issues?"

**What the system returned:** The refusal message — *"I'm sorry, but that information isn't available in the student reviews and parking logs."* — even though related information *does* exist in the corpus (in `Parking.txt`, a commenter says you can "get a commuter red permit and take a bus from the Jackson Avenue lot all over campus… here's the bus system: outransit.com," and another mentions parking off-campus and taking "the bus for free into campus").

**Root cause (tied to a specific pipeline stage):** This is a **retrieval-stage failure caused by domain-specific vocabulary mismatch**, compounded by correct grounding behavior at the generation stage.

- The query hinges on the term **"OUT bus"** (Oxford University Transit). But *the documents never use that phrase* — they say "the bus," "a bus from the Jackson Avenue lot," or link to `outransit.com`. The `all-MiniLM-L6-v2` embedding model has no learned association between the acronym "OUT bus" and these plain-language phrasings, so the query vector lands far (cosine distance ~0.41–0.46, much higher than my 0.22–0.40 hits on other questions) from the one chunk that actually answers it. As a result, the single most relevant chunk (the `outransit.com` comment) ranked **below the top-4 cutoff** and was never passed to the LLM.
- The generation stage then behaved *exactly as designed*: the four chunks it did receive only mention the bus tangentially, so under the strict grounding prompt the model correctly refused rather than stitch together a guess. The grounding worked; the retrieval starved it of the right context.

This failure is the concrete realization of the "domain-specific language and slang" risk I flagged in `planning.md` — a general-purpose embedding model can't bridge hyper-local jargon.

**What you would change to fix it:** Three options, cheapest first: (1) raise top-k to 5–6 so the borderline `outransit.com` chunk clears the cutoff; (2) add a lightweight synonym/alias expansion that rewrites "OUT bus" → "Oxford University Transit / outransit / campus bus" before embedding the query; (3) the robust fix — fine-tune or swap in an embedding model that understands local terminology, so "OUT bus" and "take the bus from the Jackson Avenue lot" map close together in vector space.

---

## Spec Reflection

**One way the spec helped you during implementation:**
The `planning.md` Chunking Strategy and Retrieval Approach sections gave me hard, unambiguous targets — 500-character chunks, 100-character overlap, `all-MiniLM-L6-v2`, top-k = 4 — *before* any code existed. Because those numbers were fixed in advance, I could direct the AI to implement precisely to spec and immediately verify the output (chunk count, distances) against a known intent rather than guessing parameters mid-build. The Evaluation Plan table was equally valuable: having 5 questions with expected answers written upfront turned "does it work?" into a concrete, testable checklist and gave me the exact ground truth used in the Evaluation Report above.

**One way your implementation diverged from the spec, and why:**
The spec described a single, uniform `RecursiveCharacterTextSplitter` pass over all documents. My implementation diverged by adding a **two-stage, header-aware split with contextual prefixes** for the structured review document. During testing I noticed that *The Good The Bad, and The Ugly* — a thread organized by apartment under "Good/Bad/Ugly" headers — was being chopped purely by character count, so long reviews split across boundaries and the tail chunks no longer said *which apartment* they were about. A retrieved chunk would describe broken gates and rodents with no idea it was about "The Domain." To fix this I restructured that file with Markdown headers and added `MarkdownHeaderTextSplitter` + a `[Apartment — Category]` prefix so the apartment context is preserved on every chunk. The 500/100 character split is still intact; I layered structure-awareness on top of it because pure character chunking destroyed the semantic self-containment the spec was trying to achieve in the first place.

---

## AI Usage

**Instance 1 — Refining my prompts with an external AI before sending them to Claude Code**

- *What I gave the AI:* For each milestone, I first wrote my own implementation prompt based on the milestone description (e.g., "build an ingestion + chunking script using RecursiveCharacterTextSplitter at 500/100 with source metadata"). Before sending it to Claude Code in my IDE, I pasted that draft prompt into Gemini (a separate chat, outside the IDE) and asked it to critique the prompt — what details I was missing, what edge cases I should specify, and what could go wrong with my phrasing.
- *What it produced:* Gemini returned suggestions on tightening the prompt — things like explicitly specifying metadata fields, asking for a verification/test block, and calling out failure modes (empty chunks, duplicate vectors) I hadn't thought to mention.
- *What I changed or directed differently:* I folded the useful suggestions into my prompt and dropped the ones that over-complicated the milestone, then sent the refined version to Claude Code to actually generate and run the script. This two-step loop (draft → external critique → execute) meant Claude received clearer, more complete specs and produced code that needed fewer correction rounds. I treated Gemini as a prompt reviewer, not a code generator.

**Instance 2 — Overriding the character-only chunking when it lost apartment context**

- *What I gave the AI:* I gave Claude Code my Chunking Strategy (500 char / 100 overlap, RecursiveCharacterTextSplitter, source metadata) and had it implement the cleaning + chunking pipeline.
- *What it produced:* A working script that cleaned the Reddit UI noise and split every document purely on character count, attaching the source filename to each chunk.
- *What I changed or directed differently:* When I inspected the output I noticed one source — the Reddit thread with topic headers ("The Good/Bad/Ugly," organized per apartment) — was being cut mid-review, so chunks talked about a specific apartment's problems without the chunk itself recording *which* apartment, and the apartment wasn't tracked appropriately. I redirected the approach: instead of treating that file like the others, I had the cleaning step add topic/section headers to the raw `.txt` when cleaning, then split header-aware so each chunk carries its apartment/category as metadata and a `[Apartment — Category]` prefix. This was a direction change I drove based on reading the actual chunk output — the AI's first implementation was correct to spec but semantically inadequate for that one structured document.
