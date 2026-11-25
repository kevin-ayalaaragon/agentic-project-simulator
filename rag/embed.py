"""Embeddings for the retrieval layer.

`Embedder` is the seam: the MVP uses bge-small-en-v1.5 through fastembed (ONNX
Runtime, no torch), and a hosted model such as Voyage can be added later as a
comparison row without touching the store. Corpus vectors are computed once and
committed with the manifest, so CI never downloads the model.

bge expects queries prefixed with an instruction and passages without one; the
prefix is recorded in the manifest so query vectors stay comparable.

Usage: python -m rag.embed   (downloads the model on first run)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Protocol

import numpy as np

HERE = Path(__file__).resolve().parent / "corpus"
MODEL = "BAAI/bge-small-en-v1.5"
DIM = 384
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
# The quantized ONNX build fastembed serves for MODEL, pinned for the record:
ONNX_REPO = "Qdrant/bge-small-en-v1.5-onnx-Q"
ONNX_REVISION = "aa8f8b060edb00e03bfdd08813a2949946c8ba55"
ONNX_SHA256 = "51f1bd0addd6e859e42c2c8021a5e5461385bb676a649f4b269aa445449f2431"  # model_optimized.onnx


class Embedder(Protocol):
    name: str
    dim: int

    def passages(self, texts: list[str]) -> np.ndarray: ...
    def queries(self, texts: list[str]) -> np.ndarray: ...


class FastEmbedBge:
    name, dim = MODEL, DIM

    def __init__(self) -> None:
        from fastembed import TextEmbedding  # lazy: core tests never import it

        self._model = TextEmbedding(MODEL, cache_dir=os.environ.get("FASTEMBED_CACHE_PATH"))

    def _embed(self, texts: list[str]) -> np.ndarray:
        # Small batches: full-length (~400-token) passages are memory-bound on CPU, and
        # large batches were slower, not faster. One-time cost: about 20 minutes.
        vectors = np.asarray(list(self._model.embed(texts, batch_size=8)), dtype=np.float32)
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

    def passages(self, texts: list[str]) -> np.ndarray:
        return self._embed(texts)

    def queries(self, texts: list[str]) -> np.ndarray:
        return self._embed([QUERY_PREFIX + t for t in texts])


def passage_text(chunk: dict) -> str:
    return f"{chunk['control_id'].upper()} {chunk['title']}. {chunk['body']}"


def main() -> int:
    chunks = [json.loads(line) for line in (HERE / "chunks.jsonl").read_text(encoding="utf-8").splitlines() if line]
    embedder = FastEmbedBge()
    vectors = embedder.passages([passage_text(c) for c in chunks])
    np.save(HERE / "embeddings.npy", vectors)
    manifest_path = HERE / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "embedding_model": MODEL,
        "embedding_onnx_repo": ONNX_REPO,
        "embedding_onnx_revision": ONNX_REVISION,
        "embedding_onnx_sha256": ONNX_SHA256,
        "embedding_dim": DIM,
        "normalized": True,
        "query_prefix": QUERY_PREFIX,
    })
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"embedded {len(chunks)} chunks with {MODEL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
