"""The runtime retriever `--mode rag` calls: query text in, top-k NIST chunks out.

Kept behind a plain callable so the runner can be tested with a stub and no
database or model. The default builds the store from the committed corpus and
embeds queries with the same pinned bge-small model used for the corpus.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable

Retriever = Callable[[str, int], list[dict]]

CORPUS = Path(__file__).resolve().parent / "corpus"


def default_retriever() -> Retriever:
    """Hybrid search over Postgres + pgvector. Needs PD_PG_DSN and the embedding model (downloaded once)."""
    from rag.embed import FastEmbedBge
    from rag.store import pg

    dsn = os.environ.get("PD_PG_DSN")
    if not dsn:
        raise RuntimeError("--mode rag needs PD_PG_DSN pointing at Postgres with pgvector")
    conn = pg.connect(dsn)
    pg.load(conn, CORPUS / "chunks.jsonl", CORPUS / "embeddings.npy", CORPUS / "manifest.json")
    chunks = {c["chunk_id"]: c for c in map(json.loads, (CORPUS / "chunks.jsonl").read_text(encoding="utf-8").splitlines()) if c}
    embedder = FastEmbedBge()

    def retrieve(query: str, k: int) -> list[dict]:
        ids = pg.search(conn, query, embedder.queries([query])[0], arm="hybrid", k=k)
        return [chunks[i] for i in ids]

    return retrieve
