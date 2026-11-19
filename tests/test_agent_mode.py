"""Check the read_artifact tool and the agent tool loop with a fake client; no API calls."""

import json
from pathlib import Path
from types import SimpleNamespace

import yaml

from core_engine.schemas import AgentRole, Scenario
from eval.runners import run_scenario as rs

SCENARIO = Scenario.model_validate(
    yaml.safe_load(Path("eval/scenarios/scn_007_ledger_service_circular_dependency.yaml").read_text())
)
ARTIFACTS = rs.load_artifacts(SCENARIO.id)
FINAL = {
    "agent": AgentRole.ENGINEERING_LEAD.value, "gate": SCENARIO.project_state.stage.value,
    "decision": "block",
    "concerns": [{"defect_id": "def_circular_dependency", "severity": "blocking",
                  "concern_text": "Ledger and fraud services depend on each other.", "references": []}],
    "reasoning": "Mutual hard dependencies block both Q2 releases.",
}
USAGE = SimpleNamespace(input_tokens=10, output_tokens=5)


def _tool_use(name: str):
    block = SimpleNamespace(type="tool_use", id=f"tu_{name}", input={"name": name})
    return SimpleNamespace(stop_reason="tool_use", content=[block], usage=USAGE)


def _final():
    return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=json.dumps(FINAL))], usage=USAGE)


class FakeClient:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self.replies.pop(0)


def test_every_scenario_artifact_has_text():
    for path in Path("eval/scenarios").glob("*.yaml"):
        scenario = yaml.safe_load(path.read_text())
        assert set(rs.load_artifacts(scenario["id"])) == set(scenario["project_state"]["artifacts"])


# Facts that appear only in seeded-defect descriptions, never in the scenario description.
ANSWER_KEY_ONLY = {
    "scn_003_synchronous_vendor_call_in_checkout": ["99.9"],
    "scn_005_cross_border_data_residency": ["scc"],
    "scn_006_mid_sprint_scope_addition": ["kyc", "new vendor", "staffing"],
}


def test_artifacts_do_not_leak_the_answer_key():
    for path in Path("eval/scenarios").glob("*.yaml"):
        scenario = yaml.safe_load(path.read_text())
        text = " ".join(rs.load_artifacts(scenario["id"]).values()).lower()
        for defect in scenario["seeded_defects"]:
            assert defect["id"] not in text, (scenario["id"], defect["id"])
        for fact in ANSWER_KEY_ONLY.get(scenario["id"], []):
            assert fact not in text, (scenario["id"], fact)


def test_tool_input_is_restricted_to_listed_artifacts():
    tool = rs.build_artifact_tool(ARTIFACTS)
    assert tool["strict"] is True
    assert tool["input_schema"]["properties"]["name"]["enum"] == list(ARTIFACTS)
    content, is_error = rs.run_tool(ARTIFACTS, {"name": "not_listed"})
    assert is_error and "Unknown artifact" in content


def test_agent_reads_artifacts_then_returns_structured_answer():
    client = FakeClient([_tool_use("q2_release_plan"), _tool_use("fraud_service_refactor_doc"), _final()])
    response, usage, causes = rs.call_agent(client, AgentRole.ENGINEERING_LEAD, SCENARIO, rs.load_defect_catalog(), "agent")
    assert causes == [] and response.concerns[0].defect_id == "def_circular_dependency"
    assert usage.tool_calls == ["q2_release_plan", "fraud_service_refactor_doc"]
    last_messages = client.calls[-1]["messages"]
    assert last_messages[-1]["content"][0]["type"] == "tool_result"


def test_tool_loop_stops_at_the_turn_cap():
    client = FakeClient([_tool_use("q2_release_plan")] * (2 * (rs.MAX_TOOL_TURNS + 1)))
    response, _, causes = rs.call_agent(client, AgentRole.ENGINEERING_LEAD, SCENARIO, rs.load_defect_catalog(), "agent")
    assert response is None and causes == ["max_tool_turns", "max_tool_turns"]


def test_control_prompt_carries_artifact_text_and_agent_prompt_does_not():
    catalog = rs.load_defect_catalog()
    text = ARTIFACTS["q2_release_plan"].strip()
    assert text in rs.build_user_prompt(SCENARIO, AgentRole.PM, catalog, "control", ARTIFACTS)
    assert text not in rs.build_user_prompt(SCENARIO, AgentRole.PM, catalog, "agent", ARTIFACTS)
