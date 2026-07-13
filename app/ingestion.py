"""Ingest feedback from CSV/JSON files or dicts, with validation."""
import json
from pathlib import Path

import pandas as pd
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models import Feedback, FeedbackIn


class IngestResult:
    def __init__(self) -> None:
        self.accepted = 0
        self.rejected = 0
        self.errors: list[str] = []

    def as_dict(self) -> dict:
        return {
            "accepted": self.accepted,
            "rejected": self.rejected,
            "errors": self.errors[:20],  # cap error list in responses
        }


def ingest_records(session: Session, records: list[dict]) -> IngestResult:
    """Validate and insert a batch of feedback dicts."""
    result = IngestResult()
    for i, raw in enumerate(records):
        try:
            item = FeedbackIn(**raw)
        except ValidationError as e:
            result.rejected += 1
            result.errors.append(f"row {i}: {e.errors()[0]['msg']}")
            continue
        session.add(Feedback(source=item.source, text=item.text, rating=item.rating))
        result.accepted += 1
    session.commit()
    return result


def ingest_csv(session: Session, path: str | Path) -> IngestResult:
    df = pd.read_csv(path)
    df = df.where(pd.notnull(df), None)
    records = df.to_dict(orient="records")
    # pandas floats -> ints for ratings
    for r in records:
        if r.get("rating") is not None:
            try:
                r["rating"] = int(r["rating"])
            except (TypeError, ValueError):
                r["rating"] = None
    return ingest_records(session, records)


def ingest_json(session: Session, path: str | Path) -> IngestResult:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("JSON file must contain a list of feedback objects")
    return ingest_records(session, data)
