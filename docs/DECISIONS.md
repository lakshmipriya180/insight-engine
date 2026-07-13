# Architecture Decisions

## ADR-1: Embeddings clustering over LLM-only classification

**Context:** Themes could be assigned by prompting an LLM to classify each record.
**Decision:** Cluster embeddings first; use the LLM only to *label* discovered clusters.
**Why:** Cost scales with O(themes) LLM calls instead of O(records); clustering is deterministic and reproducible; themes emerge from the data instead of a predefined taxonomy that goes stale.
**Trade-off:** Cluster boundaries are less semantically crisp than LLM judgment; mitigated by the noise bucket and keyword descriptions.

## ADR-2: HDBSCAN over KMeans

**Decision:** HDBSCAN (scikit-learn ≥ 1.3) as the primary clusterer.
**Why:** Feedback theme count is unknown ahead of time; HDBSCAN discovers it and explicitly marks outliers as noise rather than forcing them into a cluster.
**Trade-off:** Can over-assign noise on small/sparse data — handled with a looser retry and a KMeans fallback for tiny datasets.

## ADR-3: Citations by record ID, quotes copied not generated

**Decision:** Briefs may only quote text fetched from the database, always tagged `[#id, source]`.
**Why:** Hallucinated evidence is the failure mode that kills trust in AI analytics tools. The template path copies verbatim by construction; the LLM path receives quotes pre-fetched with IDs and is instructed to preserve them.
**Trade-off:** Slightly stiffer prose in the LLM brief; acceptable for a decision document.

## ADR-4: Graceful degradation everywhere

**Decision:** No API key → template brief + keyword theme labels. No sentence-transformers → TF-IDF/SVD embeddings.
**Why:** Anyone can clone and run the full loop in under a minute; demos never depend on credentials; the upgrade path is config, not code changes.

## ADR-5: SQLite default, Postgres-ready

**Decision:** SQLAlchemy ORM with `DATABASE_URL` override.
**Why:** Zero-setup local runs; the same models deploy to Postgres unchanged.

## ADR-6: Lexicon sentiment over a model (for now)

**Decision:** Deterministic lexicon scoring blended with the user rating when available.
**Why:** Zero dependencies, fully explainable, trivially unit-testable — and the interface (`sentiment_score(text, rating)`) lets a model replace it without touching callers. Eval plan for that swap is in EVALS.md.
