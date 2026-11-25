"""Reciprocal rank fusion (Cormack, Clarke and Buettcher, SIGIR 2009).

The pure-Python reference for the fusion the hybrid SQL query performs, so the
query can be checked against it in tests without trusting the database.
"""

from __future__ import annotations

RRF_K = 60


def rrf(rankings: list[list[str]], k: int = RRF_K, limit: int | None = None) -> list[tuple[str, float]]:
    """Fuse ranked ID lists: score(id) = sum over lists of 1 / (k + rank), rank from 1.

    Ties break by ID so the order is deterministic.
    """
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    fused = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return fused[:limit] if limit is not None else fused
