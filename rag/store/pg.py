"""Postgres + pgvector retrieval store.

The database is a rebuildable cache: the committed chunks.jsonl, embeddings and
manifest are the source of truth, and `load` rebuilds the table from them,
skipping the work when the stored manifest hash already matches.

`search` runs one of three arms over the same table:
  fts     full-text search, OR-combined lexemes ranked by ts_rank_cd
  vector  exact cosine nearest neighbours (no ANN index)
  hybrid  both arms, top 50 each, fused with reciprocal rank fusion in SQL
Control IDs written in the query (`AC-2(1)`) are matched exactly first, because
the full-text parser splits them into unhelpful tokens.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

import numpy as np
import psycopg
from pgvector.psycopg import register_vector

from rag.fusion import RRF_K
from rag.query import control_ids_in

SCHEMA = Path(__file__).with_name("schema.sql")
CANDIDATES = 50
Arm = Literal["fts", "vector", "hybrid"]

# Every lexeme of the query, OR-combined. plainto_tsquery would AND them, and a
# long role + artifact query would then match almost nothing. quote_literal keeps
# the already-stemmed lexemes from being stemmed a second time.
_TSQUERY = (
    "(SELECT coalesce(nullif(array_to_string(array("
    "SELECT quote_literal(l) FROM unnest(tsvector_to_array(to_tsvector('english', %(q)s))) l"
    "), ' | '), ''), '''''')::tsquery)"
)

_FTS = f"""
SELECT chunk_id, row_number() OVER (ORDER BY ts_rank_cd(tsv, q.tsq) DESC, chunk_id) AS r
FROM chunks, {_TSQUERY} AS q(tsq)
WHERE tsv @@ q.tsq
ORDER BY r LIMIT %(n)s
"""

_VECTOR = """
SELECT chunk_id, row_number() OVER (ORDER BY embedding <=> %(e)s, chunk_id) AS r
FROM chunks
ORDER BY r LIMIT %(n)s
"""

_HYBRID = f"""
WITH fts AS ({_FTS}), vec AS ({_VECTOR})
SELECT chunk_id FROM (SELECT * FROM fts UNION ALL SELECT * FROM vec) u
GROUP BY chunk_id
ORDER BY sum(1.0 / ({RRF_K} + r)) DESC, chunk_id
LIMIT %(k)s
"""


def connect(dsn: str) -> psycopg.Connection:
    conn = psycopg.connect(dsn, autocommit=True)
    conn.execute(SCHEMA.read_text(encoding="utf-8"))
    register_vector(conn)
    return conn


def load(conn: psycopg.Connection, chunks_path: Path, embeddings_path: Path, manifest_path: Path) -> bool:
    """Rebuild the table from committed artifacts. Returns False when it was already current."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    # Stamp from the files' own bytes, not the manifest's claims, so edited chunks or
    # rebuilt embeddings always trigger a reload.
    stamp = ":".join(
        [hashlib.sha256(chunks_path.read_bytes()).hexdigest(),
         hashlib.sha256(embeddings_path.read_bytes()).hexdigest(),
         manifest.get("embedding_model", "")]
    )
    row = conn.execute("SELECT value FROM store_meta WHERE key = 'stamp'").fetchone()
    if row and row[0] == stamp:
        return False
    chunks = [json.loads(line) for line in chunks_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    vectors = np.load(embeddings_path)
    if len(chunks) != len(vectors):
        raise ValueError(f"{len(chunks)} chunks but {len(vectors)} embeddings")
    with conn.transaction():
        conn.execute("TRUNCATE chunks")
        with conn.cursor().copy(
            "COPY chunks (chunk_id, control_id, family, title, body, embedding) FROM STDIN WITH (FORMAT BINARY)"
        ) as copy:
            copy.set_types(["text", "text", "text", "text", "text", "vector"])
            for chunk, vector in zip(chunks, vectors):
                copy.write_row([chunk["chunk_id"], chunk["control_id"], chunk["family"],
                                chunk["title"], chunk["body"], np.asarray(vector, dtype=np.float32)])
        conn.execute(
            "INSERT INTO store_meta (key, value) VALUES ('stamp', %s) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            (stamp,),
        )
    return True


def search(conn: psycopg.Connection, query: str, embedding: np.ndarray, arm: Arm = "hybrid", k: int = 10) -> list[str]:
    """Ranked chunk IDs: exact control-ID matches first, then the chosen arm."""
    params = {"q": query, "e": np.asarray(embedding, dtype=np.float32), "n": CANDIDATES, "k": k}
    sql = {"fts": _FTS, "vector": _VECTOR, "hybrid": _HYBRID}[arm]
    ranked = [r[0] for r in conn.execute(sql, params).fetchall()]
    exact: list[str] = []
    ids = control_ids_in(query)
    if ids:
        rows = conn.execute(
            "SELECT chunk_id FROM chunks WHERE control_id = ANY(%s) ORDER BY array_position(%s, control_id), chunk_id",
            (ids, ids),
        ).fetchall()
        exact = [r[0] for r in rows]
    return (exact + [c for c in ranked if c not in exact])[:k]
