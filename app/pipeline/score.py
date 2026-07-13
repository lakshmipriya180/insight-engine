"""Sentiment and urgency scoring.

Lightweight lexicon-based scoring — zero extra dependencies, deterministic,
easy to eval against. Swap in a model later without changing the interface.
"""
import re

POSITIVE = {
    "love", "great", "excellent", "amazing", "awesome", "fantastic", "perfect",
    "helpful", "easy", "intuitive", "fast", "reliable", "smooth", "beautiful",
    "best", "good", "happy", "impressed", "wonderful", "seamless",
}
NEGATIVE = {
    "hate", "terrible", "awful", "horrible", "broken", "bug", "crash", "crashes",
    "slow", "confusing", "frustrating", "frustrated", "useless", "bad", "worst",
    "annoying", "disappointed", "disappointing", "fails", "failed", "error",
    "unusable", "laggy", "glitch", "missing", "lost", "wrong",
}
URGENT = {
    "crash", "crashes", "crashed", "data loss", "lost data", "cannot", "can't",
    "refund", "cancel", "cancelling", "canceling", "unsubscribe", "churn",
    "urgent", "immediately", "blocked", "broken", "security", "leak", "charged",
    "double charged", "payment failed", "unusable", "down",
}

_WORD_RE = re.compile(r"[a-z']+")


def sentiment_score(text: str, rating: int | None = None) -> float:
    """Return sentiment in [-1, 1]. Rating (1-5) blended in when present."""
    words = _WORD_RE.findall(text.lower())
    if not words:
        lex = 0.0
    else:
        pos = sum(w in POSITIVE for w in words)
        neg = sum(w in NEGATIVE for w in words)
        lex = (pos - neg) / max(1, pos + neg) if (pos + neg) else 0.0

    if rating is not None:
        rating_signal = (rating - 3) / 2  # 1..5 -> -1..1
        return round(0.5 * lex + 0.5 * rating_signal, 3)
    return round(lex, 3)


def urgency_score(text: str, rating: int | None = None) -> float:
    """Return urgency in [0, 1] based on urgent-term hits, caps, and rating."""
    lower = text.lower()
    hits = sum(term in lower for term in URGENT)
    score = min(1.0, hits * 0.3)
    if text.isupper() and len(text) > 20:  # ALL-CAPS rant
        score = min(1.0, score + 0.2)
    if "!" in text:
        score = min(1.0, score + 0.05 * text.count("!"))
    if rating == 1:
        score = min(1.0, score + 0.2)
    return round(score, 3)


def suggested_action(avg_sentiment: float, avg_urgency: float, size: int) -> str:
    """Map theme stats to a suggested action."""
    if avg_urgency >= 0.4 and size >= 5:
        return "fix"
    if avg_sentiment <= -0.2:
        return "investigate"
    return "monitor"
