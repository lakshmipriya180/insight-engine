"""Pipeline orchestrator: embed -> cluster -> label -> score -> persist themes."""
import os

from sqlalchemy.orm import Session

from app.models import Feedback, Theme
from app.pipeline.cluster import cluster_embeddings, top_terms_per_cluster
from app.pipeline.embed import embed_texts
from app.pipeline.score import sentiment_score, suggested_action, urgency_score


def _label_theme_llm(terms: list[str], samples: list[str]) -> str | None:
    """Ask Claude for a short human-readable theme label. Returns None on failure."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic

        client = anthropic.Anthropic()
        sample_block = "\n".join(f"- {s[:200]}" for s in samples[:5])
        msg = client.messages.create(
            model=os.getenv("BRIEF_MODEL", "claude-sonnet-5"),
            max_tokens=30,
            messages=[{
                "role": "user",
                "content": (
                    "Give a 2-5 word product-feedback theme label (no quotes, no period) "
                    f"for feedback with keywords [{', '.join(terms)}] and samples:\n{sample_block}"
                ),
            }],
        )
        label = msg.content[0].text.strip().strip('"').strip(".")
        return label[:120] if label else None
    except Exception:  # noqa: BLE001
        return None


def run_pipeline(session: Session, min_cluster_size: int | None = None) -> dict:
    """Run the full insight pipeline over all feedback records.

    min_cluster_size defaults to an adaptive value (~4% of corpus, min 8) —
    small datasets keep fine-grained themes, large ones avoid fragmentation.
    """
    records = session.query(Feedback).order_by(Feedback.id).all()
    if len(records) < 10:
        raise ValueError(f"Need at least 10 feedback records, found {len(records)}.")
    if min_cluster_size is None:
        min_cluster_size = max(8, len(records) // 25)

    texts = [r.text for r in records]

    # 1. Embed + 2. Cluster
    embeddings, backend = embed_texts(texts)
    labels = cluster_embeddings(embeddings, min_cluster_size=min_cluster_size)

    # 3. Score every record
    for rec in records:
        rec.sentiment = sentiment_score(rec.text, rec.rating)
        rec.urgency = urgency_score(rec.text, rec.rating)

    # 4. Build themes (replace previous run's themes)
    session.query(Feedback).update({Feedback.theme_id: None})
    session.query(Theme).delete()
    session.flush()

    terms_by_cluster = top_terms_per_cluster(texts, labels)
    themes_created = 0
    for cid, terms in terms_by_cluster.items():
        members = [r for r, l in zip(records, labels) if l == cid]
        if not members:
            continue
        avg_sent = round(sum(r.sentiment for r in members) / len(members), 3)
        avg_urg = round(sum(r.urgency for r in members) / len(members), 3)
        label = _label_theme_llm(terms, [m.text for m in members]) or ", ".join(terms[:3]).title()
        theme = Theme(
            label=label,
            description=f"Auto-clustered theme. Top terms: {', '.join(terms)}",
            size=len(members),
            avg_sentiment=avg_sent,
            avg_urgency=avg_urg,
            suggested_action=suggested_action(avg_sent, avg_urg, len(members)),
        )
        session.add(theme)
        session.flush()
        for m in members:
            m.theme_id = theme.id
        themes_created += 1

    session.commit()
    noise = int((labels == -1).sum()) if hasattr(labels, "sum") else 0
    return {
        "records_processed": len(records),
        "themes_created": themes_created,
        "unclustered": noise,
        "embedding_backend": backend,
    }
