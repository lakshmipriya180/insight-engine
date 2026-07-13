"""insight-engine API.

Run: uvicorn app.main:app --reload
"""
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db import get_session, init_db
from app.ingestion import ingest_records
from app.models import Brief, Feedback, FeedbackIn, FeedbackOut, Theme, ThemeOut
from app.pipeline.brief import generate_brief
from app.pipeline.run import run_pipeline

app = FastAPI(
    title="insight-engine",
    description="Turn raw customer feedback into product decisions.",
    version="0.1.0",
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/feedback", status_code=201)
def add_feedback(items: list[FeedbackIn], session: Session = Depends(get_session)) -> dict:
    """Ingest a batch of feedback records."""
    result = ingest_records(session, [i.model_dump() for i in items])
    return result.as_dict()


@app.post("/pipeline/run")
def trigger_pipeline(session: Session = Depends(get_session)) -> dict:
    """Run embed -> cluster -> score -> theme extraction."""
    try:
        return run_pipeline(session)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/themes", response_model=list[ThemeOut])
def list_themes(session: Session = Depends(get_session)):
    return session.query(Theme).order_by(desc(Theme.size)).all()


@app.get("/themes/{theme_id}/records", response_model=list[FeedbackOut])
def theme_records(theme_id: int, session: Session = Depends(get_session)):
    theme = session.get(Theme, theme_id)
    if theme is None:
        raise HTTPException(status_code=404, detail="Theme not found")
    return (
        session.query(Feedback)
        .filter(Feedback.theme_id == theme_id)
        .order_by(desc(Feedback.urgency))
        .all()
    )


@app.post("/brief")
def create_brief(session: Session = Depends(get_session)) -> dict:
    """Generate a Voice-of-Customer brief from current themes."""
    try:
        brief = generate_brief(session)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"id": brief.id, "generator": brief.generator, "content": brief.content}


@app.get("/brief/latest")
def latest_brief(session: Session = Depends(get_session)) -> dict:
    brief = session.query(Brief).order_by(desc(Brief.id)).first()
    if brief is None:
        raise HTTPException(status_code=404, detail="No brief yet — POST /brief first")
    return {"id": brief.id, "generator": brief.generator, "content": brief.content}
