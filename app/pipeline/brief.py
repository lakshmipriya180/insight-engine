"""Voice-of-Customer brief generation.

Uses Claude when ANTHROPIC_API_KEY is set; otherwise produces a deterministic
template brief. Both cite feedback by record ID — quotes are always copied
from the database, never generated, to prevent hallucinated evidence.
"""
import os
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Brief, Feedback, Theme

MODEL = os.getenv("BRIEF_MODEL", "claude-sonnet-5")
MAX_QUOTES_PER_THEME = 3


def _theme_evidence(session: Session, theme: Theme) -> list[Feedback]:
    """Most urgent records for a theme — these become the cited quotes."""
    return (
        session.query(Feedback)
        .filter(Feedback.theme_id == theme.id)
        .order_by(Feedback.urgency.desc())
        .limit(MAX_QUOTES_PER_THEME)
        .all()
    )


def _template_brief(session: Session, themes: list[Theme]) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [f"# Voice of Customer Brief — {today}", ""]
    total = sum(t.size for t in themes)
    fixes = [t for t in themes if t.suggested_action == "fix"]
    lines.append(
        f"**{total} feedback records across {len(themes)} themes.** "
        f"{len(fixes)} theme(s) need immediate attention."
    )
    lines.append("")
    for t in sorted(themes, key=lambda x: (x.suggested_action != "fix", -x.size)):
        lines.append(f"## {t.label}  `{t.suggested_action.upper()}`")
        lines.append(
            f"- **Size:** {t.size} records · **Sentiment:** {t.avg_sentiment:+.2f} "
            f"· **Urgency:** {t.avg_urgency:.2f}"
        )
        for rec in _theme_evidence(session, t):
            quote = rec.text if len(rec.text) <= 200 else rec.text[:197] + "..."
            lines.append(f'  - "{quote}" — [#{rec.id}, {rec.source}]')
        lines.append("")
    return "\n".join(lines)


def _llm_brief(session: Session, themes: list[Theme]) -> str:
    import anthropic

    client = anthropic.Anthropic()
    evidence_blocks = []
    for t in themes:
        quotes = "\n".join(
            f'  - [#{r.id}, {r.source}] "{r.text[:300]}"' for r in _theme_evidence(session, t)
        )
        evidence_blocks.append(
            f"Theme: {t.label} | size={t.size} | sentiment={t.avg_sentiment:+.2f} "
            f"| urgency={t.avg_urgency:.2f} | action={t.suggested_action}\n{quotes}"
        )
    evidence = "\n\n".join(evidence_blocks)

    prompt = f"""You are a product analyst writing a weekly Voice-of-Customer brief.

Rules:
- Use ONLY the evidence below. Quote verbatim and keep the [#id, source] citation after every quote.
- Never invent quotes, numbers, or themes.
- Structure: executive summary (3 sentences), then themes ordered by action priority
  (fix > investigate > monitor), each with stats, 1-3 cited quotes, and one recommended next step.
- Markdown format. Be concise and decision-oriented.

Evidence:
{evidence}"""

    msg = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def generate_brief(session: Session) -> Brief:
    themes = session.query(Theme).filter(Theme.size > 0).all()
    if not themes:
        raise ValueError("No themes found — run the pipeline first.")

    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            content, generator = _llm_brief(session, themes), "llm"
        except Exception:  # noqa: BLE001 — degrade gracefully on any API failure
            content, generator = _template_brief(session, themes), "template"
    else:
        content, generator = _template_brief(session, themes), "template"

    brief = Brief(content=content, generator=generator)
    session.add(brief)
    session.commit()
    return brief
