"""One-command demo: generate data (if needed) -> ingest -> pipeline -> brief.

Run from the repo root:  python scripts/load_sample_data.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db import SessionLocal, init_db  # noqa: E402
from app.ingestion import ingest_csv  # noqa: E402
from app.pipeline.brief import generate_brief  # noqa: E402
from app.pipeline.run import run_pipeline  # noqa: E402

CSV = ROOT / "data" / "sample_feedback.csv"


def load_sample_data(session) -> str:
    """Generate data if needed, ingest -> pipeline -> brief. Returns the brief content.

    Shared by the CLI entrypoint below and the dashboard's self-seed path, so
    both stay in lockstep with a single source of truth for the demo flow.
    """
    if not CSV.exists():
        print("Sample data not found — generating it first...")
        import scripts.generate_synthetic_data as gen
        gen.main()

    result = ingest_csv(session, CSV)
    print(f"Ingested: {result.accepted} accepted, {result.rejected} rejected")

    stats = run_pipeline(session)
    print(f"Pipeline: {stats}")

    brief = generate_brief(session)
    out = ROOT / "docs" / "sample_brief.md"
    out.write_text(brief.content, encoding="utf-8")
    print(f"Brief ({brief.generator}) saved to {out}")
    return brief.content


def main() -> None:
    init_db()
    session = SessionLocal()
    try:
        content = load_sample_data(session)
        print("\n--- Brief preview ---\n")
        print(content[:1500])
    finally:
        session.close()


if __name__ == "__main__":
    main()
