"""Offline tests for the retrieval layer's pure-Python parts: fusion, L3 metrics, query building."""

import inspect
from pathlib import Path

import pytest
import yaml

from core_engine.schemas import AgentRole, Scenario
from eval.metrics.retrieval import (
    bootstrap_ci,
    collapse_to_controls,
    recall_at_k,
    reciprocal_rank,
    score_queries,
)
from rag.fusion import rrf
from rag.query import build_query, control_ids_in

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = sorted((ROOT / "eval" / "scenarios").glob("*.yaml"))
ARTIFACTS = yaml.safe_load((ROOT / "eval" / "artifacts.yaml").read_text(encoding="utf-8"))


# --- fusion ---------------------------------------------------------------- #

def test_rrf_sums_reciprocal_ranks():
    fused = dict(rrf([["a", "b"], ["b", "c"]], k=60))
    assert fused["b"] == pytest.approx(1 / 62 + 1 / 61)
    assert fused["a"] == pytest.approx(1 / 61)


def test_rrf_breaks_ties_by_id_and_limits():
    assert [i for i, _ in rrf([["b"], ["a"]])] == ["a", "b"]
    assert len(rrf([["a", "b", "c"]], limit=2)) == 2


# --- metrics --------------------------------------------------------------- #

def test_chunks_collapse_to_first_occurrence_of_each_control():
    assert collapse_to_controls(["ac-2#2", "au-11", "ac-2#1", "sc-28"]) == ["ac-2", "au-11", "sc-28"]


def test_split_control_cannot_take_two_recall_slots():
    scores = score_queries({"q": ["ac-2#1", "ac-2#2", "au-11"]}, {"q": {"ac-2", "au-11"}}, ks=(2,))
    assert scores["q"]["recall@2"] == 1.0


def test_recall_and_mrr():
    assert recall_at_k(["x", "a", "b"], {"a", "c"}, 2) == 0.5
    assert reciprocal_rank(["x", "a"], {"a"}) == 0.5
    assert reciprocal_rank(["x"], {"a"}) == 0.0
    with pytest.raises(ValueError):
        recall_at_k(["a"], set(), 5)


def test_bootstrap_is_seeded_and_brackets_the_mean():
    values = {f"q{i}": i / 10 for i in range(10)}
    clusters = {f"q{i}": f"s{i // 2}" for i in range(10)}
    first = bootstrap_ci(values, clusters, seed=1)
    assert first == bootstrap_ci(values, clusters, seed=1)
    mean, low, high = first
    assert low <= mean <= high


# --- query builder --------------------------------------------------------- #

def test_query_builder_cannot_receive_a_scenario():
    params = inspect.signature(build_query).parameters
    assert "scenario" not in params
    assert all(p.annotation not in (Scenario, "Scenario") for p in params.values())


@pytest.mark.parametrize("path", SCENARIOS, ids=lambda p: p.stem)
def test_query_has_no_seeded_defect_text(path):
    scenario = Scenario.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    query = build_query(scenario.project_state, ARTIFACTS.get(scenario.id, {}), AgentRole.SECURITY_PRIVACY).lower()
    assert "def_" not in query
    for defect in scenario.seeded_defects:
        assert defect.id.lower() not in query
        assert defect.description.lower() not in query


def test_query_builder_rejects_roles_without_a_focus():
    scenario = Scenario.model_validate(yaml.safe_load(SCENARIOS[0].read_text(encoding="utf-8")))
    with pytest.raises(ValueError):
        build_query(scenario.project_state, {}, AgentRole.PM)


def test_control_ids_normalize_to_oscal_form():
    assert control_ids_in("See AC-2(1), au-11 and AC-2 (1) again") == ["ac-2.1", "au-11"]


# --- corpus builder -------------------------------------------------------- #

from rag.corpus.build import CHUNKS, MANIFEST, build, git_blob_sha1  # noqa: E402


def test_builder_skips_withdrawn_renders_params_and_splits_long_items():
    catalog = {"catalog": {"groups": [{"id": "au", "controls": [{
        "id": "au-11", "title": "Audit Record Retention",
        "parts": [
            {"name": "statement", "prose": "Retain audit records for {{ insert: param, au-11_odp }}."},
            {"name": "guidance", "prose": "Organizations retain audit records. " * 200},
        ],
        "controls": [{"id": "au-11.1", "title": "Withdrawn", "props": [{"name": "status", "value": "withdrawn"}]}],
    }]}]}}
    rows = build(catalog)
    assert {r["control_id"] for r in rows} == {"au-11"}
    assert [r["chunk_id"] for r in rows] == ["au-11#1", "au-11#2", "au-11#3"]
    assert "[Assignment]" in rows[0]["body"]
    assert all(len(r["body"].split()) <= 300 for r in rows)


def test_git_blob_hash_matches_git():
    assert git_blob_sha1(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"


@pytest.mark.skipif(not CHUNKS.exists(), reason="corpus not built yet (python -m rag.corpus.build)")
def test_built_corpus_is_clean_unique_and_matches_manifest():
    import hashlib
    import json

    data = CHUNKS.read_bytes()
    rows = [json.loads(line) for line in data.decode("utf-8").splitlines() if line]
    ids = [r["chunk_id"] for r in rows]
    assert len(ids) == len(set(ids))
    assert "def_" not in data.decode("utf-8")
    assert all(len(r["body"].split()) <= 300 for r in rows)
    assert hashlib.sha256(data).hexdigest() == json.loads(MANIFEST.read_text())["corpus_sha256"]


def test_unscorable_queries_drop_with_their_vectors():
    np = pytest.importorskip("numpy")
    from eval.retrieval.run_l3 import scorable

    queries = [{"id": "a", "relevant": {"x"}}, {"id": "b", "relevant": set()}, {"id": "c", "relevant": {"y"}}]
    vectors = np.array([[1.0], [2.0], [3.0]])
    kept, kept_vectors, unscored = scorable(queries, vectors)
    assert [q["id"] for q in kept] == ["a", "c"]
    assert kept_vectors.tolist() == [[1.0], [3.0]]
    assert unscored == ["b"]
    with pytest.raises(ValueError):
        scorable(queries, vectors[:2])


def test_embedding_model_file_must_match_the_pinned_hash(tmp_path):
    pytest.importorskip("numpy")  # rag.embed needs it; the default CI job does not install it
    from rag.embed import ONNX_REPO, ONNX_REVISION, verify_model_file

    with pytest.raises(RuntimeError, match="not found"):
        verify_model_file(tmp_path)
    model = tmp_path / f"models--{ONNX_REPO.replace('/', '--')}" / "snapshots" / ONNX_REVISION / "model_optimized.onnx"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"not the pinned model")
    with pytest.raises(RuntimeError, match="hash mismatch"):
        verify_model_file(tmp_path)
