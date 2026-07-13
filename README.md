# insight-engine 🔍

**Turn raw customer feedback into product decisions.**

insight-engine ingests unstructured customer feedback (app reviews, NPS surveys, support tickets), automatically clusters it into themes, scores sentiment and urgency, and generates an executive-ready Voice-of-Customer brief — with every quote cited back to its source record.

## Why I built this

Product teams drown in feedback but starve for insight. Most feedback dies in spreadsheets. I wanted a production-shaped AI product that closes the loop: raw text in → prioritized, evidence-backed product decisions out.

## What it does

- **Ingest** — CSV/JSON files or REST API; validated with Pydantic (sample dataset included)
- **Understand** — embeddings-based theme clustering, no predefined categories (HDBSCAN)
- **Score** — sentiment and urgency per record; fix / investigate / monitor action per theme
- **Brief** — weekly Voice-of-Customer report with quotes cited by record ID (never invented)
- **Explore** — Streamlit dashboard: KPIs, priority map, theme drill-down, latest brief

## Quickstart

```bash
pip install -r requirements.txt
python scripts/load_sample_data.py     # generate data -> ingest -> pipeline -> brief
uvicorn app.main:app --reload          # REST API at http://localhost:8000/docs
streamlit run dashboard/app.py         # dashboard
```

Runs fully offline out of the box. Two optional upgrades:

| Env / dependency | Effect |
|---|---|
| `ANTHROPIC_API_KEY` set | Theme labels + brief written by Claude (else: keyword labels + template brief) |
| `pip install sentence-transformers` | MiniLM embeddings (else: TF-IDF + SVD) |

## Architecture

```
CSV/JSON/API → FastAPI → SQLite/Postgres
                             │
              embed (MiniLM | TF-IDF fallback)
                             │
              cluster (HDBSCAN, no fixed k)
                             │
              score (sentiment, urgency) → themes + suggested actions
                             │
              VoC brief (Claude | template fallback, cited quotes)
                             │
                    Streamlit dashboard
```

Key decisions and trade-offs are logged in [docs/DECISIONS.md](docs/DECISIONS.md). Product spec in [docs/PRODUCT_SPEC.md](docs/PRODUCT_SPEC.md). Quality evaluation approach in [docs/EVALS.md](docs/EVALS.md).

## API

| Method | Route | Purpose |
|---|---|---|
| POST | `/feedback` | Ingest a batch of feedback records |
| POST | `/pipeline/run` | Run embed → cluster → score |
| GET | `/themes` | List themes with stats + suggested action |
| GET | `/themes/{id}/records` | Drill into a theme's records |
| POST | `/brief` | Generate a Voice-of-Customer brief |
| GET | `/brief/latest` | Fetch the most recent brief |

## Tests

```bash
pytest
```

Covers ingestion validation, pipeline clustering, scoring behavior, and citation guarantees in briefs.

## Roadmap

- [ ] Slack webhook delivery for weekly briefs
- [ ] Eval harness: LLM theme labels vs. human labels on 200 records
- [ ] Feedback-to-roadmap suggestion agent
- [ ] Postgres + docker-compose deployment recipe
