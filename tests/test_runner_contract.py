"""Check the gate rule and the agent output contract without calling the API."""

import pytest
from pydantic import ValidationError

from core_engine.schemas import AgentResponse, AgentRole, GateDecision, GateOutcome
from eval.runners.run_scenario import (
    _lowercase_enums,
    aggregate_outcome,
    build_output_model,
    load_defect_catalog,
)

GATE = "design_gate"


def _response(decision: str, defect_id: str | None = None) -> dict:
    concerns = []
    if defect_id is not None:
        concerns.append({"defect_id": defect_id, "severity": "high",
                         "concern_text": "PII is logged in plaintext.", "references": []})
    return {"agent": AgentRole.PM.value, "gate": GATE, "decision": decision,
            "concerns": concerns, "reasoning": "Assessment of the project at this gate."}


@pytest.mark.parametrize("decisions, expected", [
    (["approve", "approve"], GateOutcome.APPROVED),
    (["approve", "approve_with_conditions"], GateOutcome.APPROVED_WITH_CONDITIONS),
    (["approve_with_conditions", "block"], GateOutcome.BLOCKED),
])
def test_gate_rule_precedence(decisions, expected):
    responses = [AgentResponse.model_validate(_response(d)) for d in decisions]
    assert aggregate_outcome(responses) == expected


def test_output_model_rejects_defect_id_outside_catalog():
    model = build_output_model(AgentRole.PM, GATE, load_defect_catalog())
    with pytest.raises(ValidationError):
        model.model_validate(_response("block", "def_not_in_catalog"))


def test_output_model_rejects_other_agent_role():
    model = build_output_model(AgentRole.PM, GATE, load_defect_catalog())
    with pytest.raises(ValidationError):
        model.model_validate({**_response("approve"), "agent": AgentRole.FINOPS_LEGAL.value})


def test_enum_casing_is_normalized_before_validation():
    model = build_output_model(AgentRole.PM, GATE, load_defect_catalog())
    data = _lowercase_enums({**_response("BLOCK", "DEF_PII_IN_LOGS"), "agent": "PM_AGENT"})
    parsed = model.model_validate(data)
    assert parsed.decision == GateDecision.BLOCK
    assert parsed.concerns[0].defect_id == "def_pii_in_logs"
