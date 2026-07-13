import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.ingestion import ingest_records
from app.models import Base, Theme
from app.pipeline.brief import generate_brief
from app.pipeline.run import run_pipeline
from app.pipeline.score import sentiment_score, suggested_action, urgency_score


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _seed(session, n_per_theme=15):
    sync = [{"source": "ticket", "text": f"Sync failed and I lost my notes again, attempt {i}. The mobile app keeps losing data when syncing.", "rating": 1} for i in range(n_per_theme)]
    praise = [{"source": "review", "text": f"The onboarding setup wizard was easy and intuitive, running in minutes. Loved it, session {i}.", "rating": 5} for i in range(n_per_theme)]
    search = [{"source": "survey", "text": f"Please add search filters by date and tag, fuzzy matching too. Request number {i}.", "rating": 3} for i in range(n_per_theme)]
    ingest_records(session, sync + praise + search)


def test_pipeline_creates_themes(session):
    _seed(session)
    stats = run_pipeline(session, min_cluster_size=5)
    assert stats["records_processed"] == 45
    assert stats["themes_created"] >= 2
    themes = session.query(Theme).all()
    assert all(t.size > 0 for t in themes)


def test_pipeline_requires_minimum_records(session):
    ingest_records(session, [{"source": "review", "text": "Only one record here"}])
    with pytest.raises(ValueError):
        run_pipeline(session)


def test_sentiment_direction():
    assert sentiment_score("I love this, it is excellent and fast", 5) > 0.3
    assert sentiment_score("Terrible, broken, crashes constantly", 1) < -0.3


def test_urgency_detects_critical_language():
    assert urgency_score("The app crashed and I lost data, need refund immediately!", 1) > 0.5
    assert urgency_score("Nice colors on the new theme", 4) < 0.2


def test_suggested_action_mapping():
    assert suggested_action(-0.8, 0.7, 20) == "fix"
    assert suggested_action(-0.5, 0.1, 10) == "investigate"
    assert suggested_action(0.6, 0.0, 10) == "monitor"


def test_brief_generation_cites_record_ids(session, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    _seed(session)
    run_pipeline(session, min_cluster_size=5)
    brief = generate_brief(session)
    assert brief.generator == "template"
    assert "[#" in brief.content  # citations present
    assert "Voice of Customer" in brief.content


def test_brief_without_pipeline_raises(session):
    with pytest.raises(ValueError):
        generate_brief(session)
