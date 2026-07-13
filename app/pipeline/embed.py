"""Text embeddings.

Prefers sentence-transformers (all-MiniLM-L6-v2) when installed; falls back to
TF-IDF + SVD so the pipeline runs anywhere with scikit-learn alone.
"""
import numpy as np

_ST_MODEL = None


def _try_sentence_transformers():
    global _ST_MODEL
    if _ST_MODEL is not None:
        return _ST_MODEL
    try:
        from sentence_transformers import SentenceTransformer

        _ST_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        return _ST_MODEL
    except ImportError:
        return None


def embed_texts(texts: list[str]) -> tuple[np.ndarray, str]:
    """Return (embeddings, backend_name)."""
    model = _try_sentence_transformers()
    if model is not None:
        return np.asarray(model.encode(texts, show_progress_bar=False)), "sentence-transformers"

    # Fallback: TF-IDF -> truncated SVD (LSA), unit-normalized.
    # Unigrams + low-dimensional LSA: measured on the sample dataset, this
    # recovers planted themes far better than high-dim bigram vectors, which
    # fragment near-duplicate texts into micro-clusters (see docs/EVALS.md).
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize

    vec = TfidfVectorizer(stop_words="english", max_features=5000)
    X = vec.fit_transform(texts)
    n_components = min(16, X.shape[1] - 1, len(texts) - 1)
    if n_components < 2:
        return normalize(X.toarray()), "tfidf"
    svd = TruncatedSVD(n_components=n_components, random_state=42)
    return normalize(svd.fit_transform(X)), "tfidf-svd"
