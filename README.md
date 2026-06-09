# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

The Oxford/Ole Miss Off-Campus Housing & Commuting Reality Check.
     This is useful because of the competetive hosuing market for Ole Miss students, will equip upcoming students with the knowledge they need to make the best decesion for their stay in Oxford.This knowledge is crucial for students but is entirely absent from the official Ole Miss housing and transit websites.


---

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

## Document Sources
     
| # | Source | Type | URL or file path |
| --- | --- | --- | --- |
| 1 | r/olemiss - Looking for Apartments In Oxford MS - The Good The Bad, and The Ugly | Reddit Thread | `[https://www.reddit.com/r/olemiss/comments/1ftqigl/looking_for_apartments_in_oxford_ms_the_good_the/](https://www.reddit.com/r/olemiss/comments/1ftqigl/looking_for_apartments_in_oxford_ms_the_good_the/)` |
| 2 | r/olemiss - cheap Oxford Apartments near OleMiss | Reddit Thread | `[https://www.reddit.com/r/olemiss/comments/171g7lp/cheap_oxford_apartments_near_olemiss/](https://www.reddit.com/r/olemiss/comments/171g7lp/cheap_oxford_apartments_near_olemiss/)` |
| 3 | r/olemiss - apartment complex recommendations | Reddit Thread | `[https://www.reddit.com/r/olemiss/comments/f33vv7/apartment_complex_recommendations/](https://www.reddit.com/r/olemiss/comments/f33vv7/apartment_complex_recommendations/)` |
| 4 | r/olemiss - Avoid Azul Apartments In Oxford at all Costs | Reddit Thread | `[https://www.reddit.com/r/olemiss/comments/1ft6hbz/avoid_azul_apartments_in_oxford_at_all_costs/](https://www.reddit.com/r/olemiss/comments/1ft6hbz/avoid_azul_apartments_in_oxford_at_all_costs/)` |
| 5 | r/olemiss - Northgate Apartments? (On-campus upperclassmen/grad housing) | Reddit Thread | `[https://www.reddit.com/r/olemiss/comments/1t1q61t/northgate_apartments/](https://www.reddit.com/r/olemiss/comments/1t1q61t/northgate_apartments/)` |
| 6 | r/olemiss - Parking on campus? (Morning lot fill-up times) | Reddit Thread | `[https://www.reddit.com/r/olemiss/comments/1t0elp2/parking_on_campus/](https://www.reddit.com/r/olemiss/comments/1t0elp2/parking_on_campus/)` |
| 7 | r/olemiss - Parking (Strict enforcement, Commuter Red passes, and OUT bus) | Reddit Thread | `[https://www.reddit.com/r/olemiss/comments/1n2p7f7/parking/](https://www.reddit.com/r/olemiss/comments/1n2p7f7/parking/)` |
| 8 | r/olemiss - Parking after 5 (Unwritten 5 PM to 7 AM zone rules) | Reddit Thread | `[https://www.reddit.com/r/olemiss/comments/1f21o0d/parking_after_5/](https://www.reddit.com/r/olemiss/comments/1f21o0d/parking_after_5/)` |
| 9 | r/olemiss - Where is a good place to park? (Visitor parking & temporary passes) | Reddit Thread | `[https://www.reddit.com/r/olemiss/comments/1dz35ug/where_is_a_good_place_to_park/](https://www.reddit.com/r/olemiss/comments/1dz35ug/where_is_a_good_place_to_park/)` |
| 10 | r/olemiss - Gameday Parking (Shuttles, Jackson Avenue Center, and paid local lots) | Reddit Thread | `[https://www.reddit.com/r/olemiss/comments/1owxytm/gameday_parking/](https://www.reddit.com/r/olemiss/comments/1owxytm/gameday_parking/)` |

---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

**Chunk size:**

**Overlap:**

**Why these choices fit your documents:**

**Final chunk count:**

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:**

**Production tradeoff reflection:**

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**

**How source attribution is surfaced in the response:**

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:**

**What the system returned:**

**Root cause (tied to a specific pipeline stage):**

**What you would change to fix it:**

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**

**One way your implementation diverged from the spec, and why:**

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- *What I gave the AI:*
- *What it produced:*
- *What I changed or overrode:*

**Instance 2**

- *What I gave the AI:*
- *What it produced:*
- *What I changed or overrode:*
