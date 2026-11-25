"""--mode rag with a fake client and a stub retriever; no API calls, no database, no model."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from pydantic import ValidationError

from core_engine.schemas import AgentRole, Scenario
from eval.metrics.citations import citation_stats
from eval.runners import run_scenario as rs

SCENARIO = Scenario.model_validate(yaml.safe_load(Path("eval/scenarios/scn_001_pii_logging.yaml").read_text()))
CATALOG = rs.load_defect_catalog()
CHUNKS = [
    {"chunk_id": "au-3.3", "control_id": "au-3.3", "title": "Limit Personally Identifiable Information Elements", "body": "Limit PII in audit records."},
    {"chunk_id": "sc-28", "control_id": "sc-28", "title": "Protection of Information at Rest", "body": "Protect information at rest."},
]
USAGE = SimpleNamespace(input_tokens=10, output_tokens=5)


class StubRetriever:
    def __init__(self):
        self.queries = []

    def __call__(self, query, k):
        self.queries.append((query, k))
        return CHUNKS


class FakeClient:
    def __init__(self, answer):
        self.answer, self.calls = answer, []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(stop_reason="end_turn", usage=USAGE,
                               content=[SimpleNamespace(type="text", text=json.dumps(self.answer))])


def _answer(agent, references):
    return {
        "agent": agent.value, "gate": SCENARIO.project_state.stage.value, "decision": "block",
        "concerns": [{"defect_id": None, "severity": "blocking",
                      "concern_text": "Full card numbers are written to application logs.", "references": references}],
        "reasoning": "Card numbers and names reach CloudWatch with no redaction layer described.",
    }


def test_rag_applies_to_security_only():
    assert rs.role_mode(AgentRole.SECURITY_PRIVACY, "rag") == "rag"
    assert rs.role_mode(AgentRole.PM, "rag") == "control"
    assert rs.role_mode(AgentRole.PM, "agent") == "agent"


def test_security_call_gets_artifacts_and_chunks_and_cites_them():
    retriever = StubRetriever()
    client = FakeClient(_answer(AgentRole.SECURITY_PRIVACY, ["AU-3.3"]))  # casing is normalized
    response, usage, causes = rs.call_agent(client, AgentRole.SECURITY_PRIVACY, SCENARIO, CATALOG, "rag", retriever)
    assert causes == [] and response.concerns[0].references == ["au-3.3"]
    assert usage.mode == "rag" and usage.retrieved == ["au-3.3", "sc-28"]
    prompt = client.calls[0]["messages"][0]["content"]
    assert "ARTIFACTS:" in prompt and "REFERENCE CONTROLS" in prompt and "[sc-28]" in prompt
    query, k = retriever.queries[0]
    assert k == rs.RAG_K and "def_" not in query
    assert all(d.description not in query for d in SCENARIO.seeded_defects)


def test_other_roles_run_as_control_without_retrieval():
    retriever = StubRetriever()
    client = FakeClient(_answer(AgentRole.PM, []))
    _, usage, causes = rs.call_agent(client, AgentRole.PM, SCENARIO, CATALOG, "rag", retriever)
    assert causes == [] and usage.mode == "control" and usage.retrieved == []
    assert retriever.queries == []
    assert "REFERENCE CONTROLS" not in client.calls[0]["messages"][0]["content"]


def test_references_are_limited_to_shown_chunks():
    model = rs.build_output_model(AgentRole.SECURITY_PRIVACY, SCENARIO.project_state.stage.value, CATALOG, ["au-3.3"])
    with pytest.raises(ValidationError):
        model.model_validate(_answer(AgentRole.SECURITY_PRIVACY, ["ac-2"]))
    plain = rs.build_output_model(AgentRole.SECURITY_PRIVACY, SCENARIO.project_state.stage.value, CATALOG, [])
    plain.model_validate(_answer(AgentRole.SECURITY_PRIVACY, ["anything"]))  # no retrieval: plain list


def test_citation_stats():
    run = {"gate_results": [{"agent_responses": [
        {"agent": "security_privacy_agent", "concerns": [{"references": ["au-3.3", "sc-28#2"]}, {"references": []}]},
        {"agent": "pm_agent", "concerns": [{"references": ["ac-2"]}]},
    ]}]}
    stats = citation_stats(run, {"security_privacy_agent"}, {"au-3.3"})
    assert (stats.concerns, stats.citing, stats.cited, stats.cited_relevant) == (2, 1, 2, 1)
    assert stats.citation_rate == 0.5 and stats.citation_relevance == 0.5
    assert citation_stats(run, {"security_privacy_agent"}, None).citation_relevance is None
