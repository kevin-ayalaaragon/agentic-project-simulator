"""L3 retrieval baseline: keyword vs vector vs hybrid on the labeled queries.

    python -m eval.retrieval.run_l3 --embed-queries   # once, downloads the model; writes query vectors
    python -m eval.retrieval.run_l3                   # needs PD_PG_DSN; writes baseline.json

Query vectors are committed with a hash of the query texts, so the CI regression
gate (tests/test_store_pg.py) runs with no model and no network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import yaml

from core_engine.schemas import AgentRole, Scenario
from eval.metrics.retrieval import bootstrap_ci, score_queries
from rag.query import build_query

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CORPUS = ROOT / "rag" / "corpus"
QUERIES = HERE / "queries.yaml"
QUERY_VECTORS = HERE / "query_embeddings.npy"
QUERY_MANIFEST = HERE / "query_manifest.json"
BASELINE = HERE / "baseline.json"
ARMS = ("fts", "vector", "hybrid")
K = 10
METRICS = ("recall@5", "recall@10", "mrr")


def load_queries() -> list[dict]:
    """Labeled queries with their text resolved; pipeline text comes from the role's view of the scenario."""
    spec = yaml.safe_load(QUERIES.read_text(encoding="utf-8"))
    artifacts = yaml.safe_load((ROOT / "eval" / "artifacts.yaml").read_text(encoding="utf-8"))
    out = []
    for q in spec["queries"]:
        text = q.get("text")
        if q["group"] == "pipeline":
            scenario = Scenario.model_validate(
                yaml.safe_load((ROOT / "eval" / "scenarios" / f"{q['scenario']}.yaml").read_text(encoding="utf-8"))
            )
            text = build_query(scenario.project_state, artifacts.get(scenario.id, {}), AgentRole.SECURITY_PRIVACY)
        out.append({**q, "text": text, "relevant": set(q["relevant"])})
    return out


def texts_sha(queries: list[dict]) -> str:
    return hashlib.sha256("\n".join(q["id"] + "\t" + q["text"] for q in queries).encode("utf-8")).hexdigest()


def load_query_vectors(queries: list[dict]) -> np.ndarray:
    manifest = json.loads(QUERY_MANIFEST.read_text(encoding="utf-8"))
    if manifest["texts_sha256"] != texts_sha(queries):
        raise SystemExit("query texts changed since the vectors were built; rerun with --embed-queries")
    return np.load(QUERY_VECTORS)


def scorable(queries: list[dict], vectors: np.ndarray) -> tuple[list[dict], np.ndarray, list[str]]:
    """Drop queries with no relevant controls (recall undefined), together with their vectors."""
    if len(queries) != len(vectors):
        raise ValueError(f"{len(queries)} queries but {len(vectors)} query vectors")
    kept = [i for i, q in enumerate(queries) if q["relevant"]]
    unscored = sorted(q["id"] for q in queries if not q["relevant"])
    return [queries[i] for i in kept], vectors[kept], unscored


def summarize(per_query: dict[str, dict[str, float]], group_of: dict[str, str]) -> dict:
    """Mean of each metric per query group and overall, plus 95% percentile-bootstrap intervals
    (2,000 resamples, seed 0, each query its own resampling unit)."""
    summary, intervals = {}, {}
    for group in ["all", *sorted(set(group_of.values()))]:
        ids = [i for i in per_query if group == "all" or group_of[i] == group]
        summary[group] = {m: round(sum(per_query[i][m] for i in ids) / len(ids), 4) for m in METRICS}
        intervals[group] = {
            m: [round(x, 4) for x in bootstrap_ci({i: per_query[i][m] for i in ids}, seed=0)[1:]] for m in METRICS
        }
    return {"summary": summary, "intervals": intervals}


def run(dsn: str, queries: list[dict], vectors: np.ndarray) -> dict:
    from rag.store import pg

    conn = pg.connect(dsn)
    pg.load(conn, CORPUS / "chunks.jsonl", CORPUS / "embeddings.npy", CORPUS / "manifest.json")
    queries, vectors, unscored = scorable(queries, vectors)
    qrels = {q["id"]: q["relevant"] for q in queries}
    groups = sorted({q["group"] for q in queries})
    result = {"k": K, "queries": len(queries), "unscored": unscored, "arms": {}}
    for arm in ARMS:
        ranked = {q["id"]: pg.search(conn, q["text"], v, arm=arm, k=K) for q, v in zip(queries, vectors)}
        per_query = score_queries(ranked, qrels)
        result["arms"][arm] = {"per_query": per_query, **summarize(per_query, {q["id"]: q["group"] for q in queries})}
    conn.close()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--embed-queries", action="store_true", help="compute and save query vectors (downloads the model)")
    parser.add_argument("--summarize", action="store_true", help="recompute means and intervals from baseline.json; no database")
    args = parser.parse_args()
    queries = load_queries()

    if args.summarize:
        baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        group_of = {q["id"]: q["group"] for q in queries}
        for arm in ARMS:
            per_query = baseline["arms"][arm]["per_query"]
            baseline["arms"][arm] = {"per_query": per_query, **summarize(per_query, group_of)}
        BASELINE.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"summarized {BASELINE.name}")
        return 0

    if args.embed_queries:
        from rag.embed import MODEL, QUERY_PREFIX, FastEmbedBge

        np.save(QUERY_VECTORS, FastEmbedBge().queries([q["text"] for q in queries]))
        QUERY_MANIFEST.write_text(json.dumps(
            {"embedding_model": MODEL, "query_prefix": QUERY_PREFIX, "texts_sha256": texts_sha(queries)},
            indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"embedded {len(queries)} queries")
        return 0

    dsn = os.environ.get("PD_PG_DSN")
    if not dsn:
        print("PD_PG_DSN not set", file=sys.stderr)
        return 1
    result = run(dsn, queries, load_query_vectors(queries))
    BASELINE.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for arm in ARMS:
        s = result["arms"][arm]["summary"]
        print(f"{arm:7s} " + "  ".join(f"{g}: R@5 {s[g]['recall@5']:.2f} MRR {s[g]['mrr']:.2f}" for g in s))
    return 0


if __name__ == "__main__":
    sys.exit(main())
