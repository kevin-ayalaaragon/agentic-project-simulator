"""Build the retrieval corpus from the NIST SP 800-53 Rev. 5 OSCAL catalog (CC0, public domain).

The raw catalog (about 10 MB) is not committed. It is fetched from a pinned commit
and checked against its git blob hash, cached in rag/corpus/raw/ (gitignored), and
turned into rag/corpus/chunks.jsonl plus rag/corpus/manifest.json, which are committed.

One chunk per active control or enhancement; withdrawn items are skipped. Text is
title + statement + guidance, with OSCAL parameter placeholders rendered as
[Assignment]. Items longer than MAX_WORDS are split on part boundaries (then on
sentences) into chunks `ac-2#1`, `ac-2#2`, so each stays within the embedding
model's 512-token window.

Usage: python -m rag.corpus.build
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

COMMIT = "5006f18c8047643eaa70e35dd0d20a58bcc41856"  # usnistgov/oscal-content, 2026-10-22
PATH = "nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json"
URL = f"https://raw.githubusercontent.com/usnistgov/oscal-content/{COMMIT}/{PATH}"
GIT_BLOB_SHA1 = "55eb9f2506cab43e051eeac6b48496246afcfd2c"
MAX_WORDS = 300  # about 400 bge tokens, under the 512-token limit

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw" / "NIST_SP-800-53_rev5_catalog.json"
CHUNKS = HERE / "chunks.jsonl"
MANIFEST = HERE / "manifest.json"

_PARAM = re.compile(r"\{\{\s*insert:\s*param,\s*[^}]+\}\}")


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def fetch() -> bytes:
    if RAW.exists():
        data = RAW.read_bytes()
    else:
        with urllib.request.urlopen(URL, timeout=60) as response:
            data = response.read()
    if git_blob_sha1(data) != GIT_BLOB_SHA1:
        raise SystemExit(f"catalog hash mismatch: expected git blob {GIT_BLOB_SHA1}")
    RAW.parent.mkdir(exist_ok=True)
    RAW.write_bytes(data)
    return data


def _prose(part: dict) -> list[str]:
    """A part's prose and its sub-parts', depth first, one string per part."""
    texts = []
    label = next((p["value"] for p in part.get("props", []) if p.get("name") == "label"), "")
    if part.get("prose"):
        texts.append(f"{label} {_PARAM.sub('[Assignment]', part['prose'])}".strip())
    for sub in part.get("parts", []):
        texts.extend(_prose(sub))
    return texts


def _withdrawn(control: dict) -> bool:
    return any(p.get("name") == "status" and p.get("value") == "withdrawn" for p in control.get("props", []))


def _pack(pieces: list[str]) -> list[str]:
    """Greedily join pieces up to MAX_WORDS; a single oversized piece is split on sentences."""
    units: list[str] = []
    for piece in pieces:
        if len(piece.split()) <= MAX_WORDS:
            units.append(piece)
        else:
            units.extend(s for s in re.split(r"(?<=[.;])\s+", piece) if s)
    chunks, current = [], []
    for unit in units:
        if current and len(" ".join(current + [unit]).split()) > MAX_WORDS:
            chunks.append(" ".join(current))
            current = []
        current.append(unit)
    if current:
        chunks.append(" ".join(current))
    return chunks


def _walk(controls: list[dict], family: str):
    for control in controls:
        if not _withdrawn(control):
            yield control, family
        yield from _walk(control.get("controls", []), family)


def build(catalog: dict) -> list[dict]:
    rows = []
    for group in catalog["catalog"]["groups"]:
        for control, family in _walk(group.get("controls", []), group["id"]):
            pieces = []
            for part in control.get("parts", []):
                if part.get("name") in ("statement", "guidance"):
                    pieces.extend(_prose(part))
            if not pieces:
                continue
            bodies = _pack(pieces)
            for n, body in enumerate(bodies, start=1):
                rows.append({
                    "chunk_id": control["id"] if len(bodies) == 1 else f"{control['id']}#{n}",
                    "control_id": control["id"],
                    "family": family,
                    "title": control["title"],
                    "body": body,
                })
    return rows


def main() -> int:
    rows = build(json.loads(fetch()))
    text = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)
    CHUNKS.write_bytes(text.encode("utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    manifest.update({
        "source": URL,
        "source_git_blob_sha1": GIT_BLOB_SHA1,
        "license": "CC0 1.0 (NIST OSCAL content)",
        "chunks": len(rows),
        "controls": len({r["control_id"] for r in rows}),
        "max_words": MAX_WORDS,
        "corpus_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    })
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{manifest['controls']} controls -> {manifest['chunks']} chunks; wrote {CHUNKS.name}, {MANIFEST.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
