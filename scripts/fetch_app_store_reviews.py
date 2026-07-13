"""Pull real customer reviews from Apple's public App Store RSS feed and run
them through the insight-engine pipeline (ingest -> cluster -> score -> brief).

No API key or auth needed -- Apple's customer-reviews RSS feed is public and
documented. This replaces whatever feedback/themes/briefs are currently in
the DB, so real reviews never end up clustered together with the synthetic
sample data from scripts/load_sample_data.py.

Usage (from repo root):
    python scripts/fetch_app_store_reviews.py --app-id 310633997          # WhatsApp, US store
    python scripts/fetch_app_store_reviews.py --app-id 310633997 --country gb --pages 8
    python scripts/fetch_app_store_reviews.py --app-id 310633997 --csv-only

Find an app's numeric id from its App Store URL, e.g.
https://apps.apple.com/us/app/whatsapp-messenger/id310633997 -> 310633997
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db import SessionLocal, init_db  # noqa: E402
from app.ingestion import ingest_records  # noqa: E402
from app.models import Brief, Feedback, Theme  # noqa: E402
from app.pipeline.brief import generate_brief  # noqa: E402
from app.pipeline.run import run_pipeline  # noqa: E402

FEED_URL = (
    "https://itunes.apple.com/{country}/rss/customerreviews/"
    "id={app_id}/sortby=mostrecent/page={page}/json"
)
USER_AGENT = "insight-engine-demo/1.0 (portfolio project; contact via GitHub)"


def fetch_page(app_id: str, country: str, page: int) -> list[dict]:
    url = FEED_URL.format(country=country, app_id=app_id, page=page)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("feed", {}).get("entry", [])


def entry_to_record(entry: dict) -> dict | None:
    rating_label = entry.get("im:rating", {}).get("label")
    content_label = entry.get("content", {}).get("label")
    title_label = entry.get("title", {}).get("label", "")
    if rating_label is None or not content_label:
        return None  # the feed's first entry is sometimes app metadata, not a review
    text = f"{title_label}. {content_label}".strip(". ").strip()
    if len(text) < 3:
        return None
    return {"source": "review", "text": text[:5000], "rating": int(rating_label)}


def fetch_reviews(app_id: str, country: str, pages: int) -> list[dict]:
    seen_ids: set[str] = set()
    records: list[dict] = []
    for page in range(1, pages + 1):
        try:
            entries = fetch_page(app_id, country, page)
        except urllib.error.HTTPError as e:
            print(f"page {page}: HTTP {e.code}, stopping")
            break
        if not entries:
            break
        new_this_page = 0
        for entry in entries:
            entry_id = entry.get("id", {}).get("label")
            if entry_id in seen_ids:
                continue
            seen_ids.add(entry_id)
            record = entry_to_record(entry)
            if record:
                records.append(record)
                new_this_page += 1
        print(f"page {page}: {new_this_page} new reviews (total {len(records)})")
        if new_this_page == 0:
            break
        time.sleep(0.3)  # be polite to Apple's endpoint
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--app-id", required=True, help="Numeric App Store id")
    parser.add_argument("--country", default="us", help="App Store storefront country code (default: us)")
    parser.add_argument("--pages", type=int, default=5, help="RSS pages to fetch, ~50 reviews/page (default: 5)")
    parser.add_argument("--csv-only", action="store_true", help="Write data/app_store_reviews.csv, skip DB/pipeline")
    args = parser.parse_args()

    records = fetch_reviews(args.app_id, args.country, args.pages)
    if not records:
        print("No reviews fetched -- check the app id and country code.")
        return

    if args.csv_only:
        import pandas as pd

        out = ROOT / "data" / "app_store_reviews.csv"
        pd.DataFrame(records).to_csv(out, index=False)
        print(f"Wrote {len(records)} reviews to {out}")
        return

    init_db()
    session = SessionLocal()
    try:
        session.query(Feedback).delete()
        session.query(Theme).delete()
        session.query(Brief).delete()
        session.commit()

        result = ingest_records(session, records)
        print(f"Ingested: {result.accepted} accepted, {result.rejected} rejected")
        if result.errors:
            print("Sample errors:", result.errors[:5])

        stats = run_pipeline(session)
        print(f"Pipeline: {stats}")
        if stats["themes_created"] == 0:
            print(
                "No dense-enough themes formed among these reviews "
                "(real-world feedback is noisier than synthetic data). "
                "Try --pages 8+ for more volume, or a different --app-id."
            )
            return

        brief = generate_brief(session)
        out = ROOT / "docs" / "app_store_brief.md"
        out.write_text(brief.content, encoding="utf-8")
        print(f"Brief ({brief.generator}) saved to {out}")
        print("\n--- Brief preview ---\n")
        print(brief.content[:1500])
    finally:
        session.close()


if __name__ == "__main__":
    main()
