"""L3: retrieval quality, scored at the control level.

Long NIST controls are split into several chunks (chunk IDs `ac-2#1`, `ac-2#2`).
Labels name controls, so a ranked chunk list is collapsed to its parent controls,
keeping first occurrence, before scoring. Otherwise one control could take
several top-k slots and be counted twice.

Labels are binary (relevant or not), so the metrics are Recall@k and MRR, as the
harness spec defines L3. Confidence intervals come from a percentile bootstrap
that resamples clusters (queries from the same scenario move together), with a
fixed seed so reported numbers reproduce exactly.
"""

from __future__ import annotations

import random
from collections import defaultdict
from statistics import mean


def control_of(chunk_id: str) -> str:
    return chunk_id.split("#", 1)[0]


def collapse_to_controls(chunk_ids: list[str]) -> list[str]:
    seen: set[str] = set()
    controls: list[str] = []
    for chunk_id in chunk_ids:
        control = control_of(chunk_id)
        if control not in seen:
            seen.add(control)
            controls.append(control)
    return controls


def recall_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        raise ValueError("recall is undefined for a query with no relevant controls")
    return len(set(ranked[:k]) & relevant) / len(relevant)


def reciprocal_rank(ranked: list[str], relevant: set[str]) -> float:
    for rank, item in enumerate(ranked, start=1):
        if item in relevant:
            return 1.0 / rank
    return 0.0


def score_queries(
    results: dict[str, list[str]],
    qrels: dict[str, set[str]],
    ks: tuple[int, ...] = (5, 10),
) -> dict[str, dict[str, float]]:
    """Per-query metrics. `results` maps query ID to ranked chunk IDs; `qrels` to relevant control IDs."""
    per_query: dict[str, dict[str, float]] = {}
    for qid, relevant in qrels.items():
        ranked = collapse_to_controls(results.get(qid, []))
        row = {f"recall@{k}": recall_at_k(ranked, relevant, k) for k in ks}
        row["mrr"] = reciprocal_rank(ranked, relevant)
        per_query[qid] = row
    return per_query


def bootstrap_ci(
    values: dict[str, float],
    clusters: dict[str, str] | None = None,
    n_resamples: int = 2000,
    seed: int = 0,
    alpha: float = 0.05,
) -> tuple[float, float, float]:
    """(mean, low, high). Resamples clusters of query IDs; each query is its own cluster by default."""
    if not values:
        raise ValueError("no values to bootstrap")
    groups: dict[str, list[float]] = defaultdict(list)
    for qid, value in values.items():
        groups[(clusters or {}).get(qid, qid)].append(value)
    keys = sorted(groups)
    rng = random.Random(seed)
    means = []
    for _ in range(n_resamples):
        sample = [v for key in rng.choices(keys, k=len(keys)) for v in groups[key]]
        means.append(mean(sample))
    means.sort()
    low = means[int(alpha / 2 * n_resamples)]
    high = means[int((1 - alpha / 2) * n_resamples) - 1]
    return mean(values.values()), low, high
