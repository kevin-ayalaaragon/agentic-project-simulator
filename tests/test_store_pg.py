"""Postgres-backed tests for the retrieval store. Skipped by default (see pytest.ini).

Run: PD_PG_DSN=postgresql://postgres@localhost:54329/pd python -m pytest -m pg
Uses a tiny fixture corpus with hand-set embeddings, so no model download is needed.
"""

import json
import os

import numpy as np
import pytest

pytestmark = pytest.mark.pg
psycopg = pytest.importorskip("psycopg")

from rag.fusion import rrf  # noqa: E402
from rag.store import pg  # noqa: E402

DSN = os.environ.get("PD_PG_DSN")

CHUNKS = [
    ("au-11", "au", "Audit Record Retention", "Retain audit records for a defined time period to support investigations."),
    ("sc-28", "sc", "Protection of Information at Rest", "Protect the confidentiality of information at rest using encryption."),
    ("ac-2.1", "ac", "Automated System Account Management", "Support account management with automated mechanisms."),
    ("si-12#1", "si", "Information Management and Retention", "Manage and retain information within the system."),
    ("si-12#2", "si", "Information Management and Retention", "Dispose of personal data when no longer needed."),
]


def _unit(*xs):
    v = np.zeros(384, dtype=np.float32)
    v[: len(xs)] = xs
    return v / np.linalg.norm(v)


VECTORS = np.stack([_unit(1, 0), _unit(0, 1), _unit(0, 0, 1), _unit(1, 0.2), _unit(0.9, 0, 0.1)])


@pytest.fixture(scope="module")
def conn(tmp_path_factory):
    if not DSN:
        pytest.skip("PD_PG_DSN not set")
    d = tmp_path_factory.mktemp("corpus")
    rows = [{"chunk_id": c, "control_id": c.split("#")[0], "family": f, "title": t, "body": b} for c, f, t, b in CHUNKS]
    (d / "chunks.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    np.save(d / "embeddings.npy", VECTORS)
    (d / "manifest.json").write_text(json.dumps({"corpus_sha256": "fixture", "embedding_model": "hand-set"}))
    connection = pg.connect(DSN)
    connection.execute("DELETE FROM store_meta")
    assert pg.load(connection, d / "chunks.jsonl", d / "embeddings.npy", d / "manifest.json") is True
    assert pg.load(connection, d / "chunks.jsonl", d / "embeddings.npy", d / "manifest.json") is False
    yield connection
    connection.close()


def test_vector_arm_is_exact_cosine_order(conn):
    # cosine to (1, 0): au-11 1.000, si-12#2 0.994, si-12#1 0.981
    assert pg.search(conn, "", _unit(1, 0), arm="vector", k=3) == ["au-11", "si-12#2", "si-12#1"]


def test_fts_arm_ors_lexemes_so_long_queries_still_match(conn):
    query = "the logging pipeline keeps audit records but nothing about tokenization or vendors"
    assert pg.search(conn, query, _unit(0, 1), arm="fts", k=3)[0] == "au-11"


def test_hybrid_matches_python_rrf_of_the_two_arms(conn):
    query, emb = "retain personal data", _unit(0, 1)
    fts = pg.search(conn, query, emb, arm="fts", k=50)
    vec = pg.search(conn, query, emb, arm="vector", k=50)
    expected = [i for i, _ in rrf([fts, vec], limit=5)]
    assert pg.search(conn, query, emb, arm="hybrid", k=5) == expected


def test_written_control_ids_rank_first(conn):
    # The parser splits "AU-11" into "au" and "-11", so the exact lookup is what finds it.
    assert pg.search(conn, "encryption at rest, see AC-2(1)", _unit(0, 1), arm="hybrid", k=3)[0] == "ac-2.1"


# --- L3 regression gate on the real corpus --------------------------------- #

from eval.retrieval import run_l3  # noqa: E402


@pytest.mark.skipif(not run_l3.BASELINE.exists(), reason="no committed L3 baseline yet")
def test_l3_scores_do_not_regress_from_baseline():
    """Rebuilds the store from committed chunks + vectors and reruns all three arms. No model, no network."""
    if not DSN:
        pytest.skip("PD_PG_DSN not set")
    queries = run_l3.load_queries()
    result = run_l3.run(DSN, queries, run_l3.load_query_vectors(queries))
    baseline = json.loads(run_l3.BASELINE.read_text(encoding="utf-8"))
    for arm in run_l3.ARMS:
        for metric, value in baseline["arms"][arm]["summary"]["all"].items():
            assert result["arms"][arm]["summary"]["all"][metric] >= value - 0.01, (arm, metric)

