"""Theme clustering via HDBSCAN (scikit-learn >= 1.3).

HDBSCAN needs no predefined cluster count and marks outliers as noise (-1),
which suits feedback data where theme count is unknown.
"""
import numpy as np
from sklearn.cluster import HDBSCAN, KMeans


def cluster_embeddings(embeddings: np.ndarray, min_cluster_size: int = 8) -> np.ndarray:
    """Return integer labels per row; -1 means noise/unclustered."""
    n = len(embeddings)
    if n < min_cluster_size * 2:
        # Tiny dataset: fall back to KMeans with a heuristic k
        k = max(2, n // 5)
        return KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(embeddings)

    labels = HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=4,
        metric="euclidean",
    ).fit_predict(embeddings)

    # If HDBSCAN calls almost everything noise, retry with a looser setting
    noise_ratio = float(np.mean(labels == -1))
    if noise_ratio > 0.6:
        labels = HDBSCAN(min_cluster_size=max(4, min_cluster_size // 2)).fit_predict(embeddings)
    return labels


def top_terms_per_cluster(
    texts: list[str], labels: np.ndarray, n_terms: int = 5
) -> dict[int, list[str]]:
    """Keyword summary per cluster (used for fallback labels + LLM context)."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    out: dict[int, list[str]] = {}
    for cid in sorted(set(labels)):
        if cid == -1:
            continue
        cluster_texts = [t for t, l in zip(texts, labels) if l == cid]
        try:
            vec = TfidfVectorizer(stop_words="english", max_features=500)
            X = vec.fit_transform(cluster_texts)
            scores = np.asarray(X.sum(axis=0)).ravel()
            terms = np.array(vec.get_feature_names_out())
            out[cid] = terms[np.argsort(scores)[::-1][:n_terms]].tolist()
        except ValueError:  # all stop-words edge case
            out[cid] = []
    return out
