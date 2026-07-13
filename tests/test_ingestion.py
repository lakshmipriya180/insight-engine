import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.ingestion import ingest_records
from app.models import Base, Feedback


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def test_ingest_valid_records(session):
    result = ingest_records(session, [
        {"source": "review", "text": "Great app, love it", "rating": 5},
        {"source": "ticket", "text": "App crashes on sync", "rating": 1},
    ])
    assert result.accepted == 2
    assert result.rejected == 0
    assert session.query(Feedback).count() == 2


def test_ingest_rejects_bad_source(session):
    result = ingest_records(session, [
        {"source": "carrier_pigeon", "text": "Hello there, nice app"},
    ])
    assert result.accepted == 0
    assert result.rejected == 1
    assert result.errors


def test_ingest_rejects_short_text(session):
    result = ingest_records(session, [{"source": "review", "text": "ok"}])
    assert result.rejected == 1


def test_ingest_normalizes_source_case(session):
    result = ingest_records(session, [{"source": "  REVIEW ", "text": "Nice and smooth app"}])
    assert result.accepted == 1
    assert session.query(Feedback).first().source == "review"


def test_ingest_mixed_batch_partial_success(session):
    result = ingest_records(session, [
        {"source": "survey", "text": "Search needs filters please", "rating": 3},
        {"source": "bad", "text": "This one is invalid"},
    ])
    assert result.accepted == 1
    assert result.rejected == 1
