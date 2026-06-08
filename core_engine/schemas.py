"""
Schemas for the Agentic Project Simulation Engine.

These are the contract between the agents, the runner, and the eval harness.
Layer 1 (schema validity) is just: did the agent's raw output parse into
one of these models? If yes, pass. If no, retry once, then fail.

Design notes:
- Keep enums small and closed. Open-ended string fields make the L1 metric
  meaningless because anything parses.
- Every agent output carries the defect IDs it claims to have caught.
  This is what makes L2 (defect detection) computable without a fuzzy
  string match between flag text and seeded defect text.
- Free-text fields (reasoning, concern_text) exist for the L4 judge and
  L5 grounding checker to evaluate, but never for the L2 scorer.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------------- #
# Enums: closed sets that constrain the model's choices.
# --------------------------------------------------------------------------- #

class AgentRole(str, Enum):
    """The fixed set of stakeholder personas in the simulator."""
    PM = "pm_agent"
    ENGINEERING_LEAD = "engineering_lead_agent"
    SECURITY_PRIVACY = "security_privacy_agent"
    FINOPS_LEGAL = "finops_legal_agent"


class GateStage(str, Enum):
    """Lifecycle gates the simulator advances projects through."""
    DESIGN = "design_gate"
    ARCHITECTURE_REVIEW = "architecture_review_gate"
    BUILD = "build_gate"
    LAUNCH_READINESS = "launch_readiness_gate"


class GateDecision(str, Enum):
    """An agent's vote at a gate. The orchestrator aggregates these."""
    APPROVE = "approve"
    BLOCK = "block"
    APPROVE_WITH_CONDITIONS = "approve_with_conditions"


class Severity(str, Enum):
    """How serious a raised concern is."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKING = "blocking"


class GateOutcome(str, Enum):
    """The aggregate result of a gate after all agents have voted."""
    APPROVED = "approved"
    BLOCKED = "blocked"
    APPROVED_WITH_CONDITIONS = "approved_with_conditions"


# --------------------------------------------------------------------------- #
# Scenario fixture: matches the YAML files in eval/scenarios/
# --------------------------------------------------------------------------- #

class SeededDefect(BaseModel):
    """One ground-truth defect planted in a scenario."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Stable identifier, e.g. def_pii_in_logs")
    description: str
    should_be_caught_by: AgentRole
    at_gate: GateStage


class ProjectState(BaseModel):
    """The project as the agents see it."""
    model_config = ConfigDict(extra="forbid")

    name: str
    stage: GateStage
    artifacts: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)


class Scenario(BaseModel):
    """One YAML test fixture, loaded into memory."""
    model_config = ConfigDict(extra="forbid")

    id: str
    category: Literal[
        "security_privacy",
        "scope_creep",
        "architecture",
        "finops_resource",
        "clean",
    ]
    description: str
    project_state: ProjectState
    seeded_defects: list[SeededDefect] = Field(default_factory=list)
    expected_gate_outcome: GateOutcome


# --------------------------------------------------------------------------- #
# Agent output: this is what each stakeholder LLM call MUST return.
# This is the schema the L1 validator checks against.
# --------------------------------------------------------------------------- #

class RaisedConcern(BaseModel):
    """A single concern an agent flags at a gate."""
    model_config = ConfigDict(extra="forbid")

    # The ID of the seeded defect this concern corresponds to, if any.
    # The agent is prompted with the list of seeded defect IDs and asked
    # to set this field when its concern maps to one. If the agent thinks
    # it has found an unseeded issue, it sets this to None.
    #
    # This is what makes L2 scoring deterministic instead of fuzzy.
    defect_id: str | None = Field(
        default=None,
        description="ID of the seeded defect this concern matches, or null if novel.",
    )
    severity: Severity
    concern_text: str = Field(
        ...,
        min_length=10,
        max_length=600,
        description="Free-text reasoning. Used by the L4 judge and L5 grounding checker.",
    )
    references: list[str] = Field(
        default_factory=list,
        description="Retrieved chunk IDs the agent cites as grounding. Used by L5.",
    )


class AgentResponse(BaseModel):
    """The full structured output from one agent's turn at one gate."""
    model_config = ConfigDict(extra="forbid")

    agent: AgentRole
    gate: GateStage
    decision: GateDecision
    concerns: list[RaisedConcern] = Field(default_factory=list)
    reasoning: str = Field(
        ...,
        min_length=20,
        max_length=1500,
        description="The agent's summary reasoning. Used by L4 and L5.",
    )


# --------------------------------------------------------------------------- #
# Run artifacts: what the runner emits per scenario, what report.py reads.
# --------------------------------------------------------------------------- #

class TokenUsage(BaseModel):
    """Cost and latency telemetry for one API call. Aggregated up the stack."""
    model_config = ConfigDict(extra="forbid")

    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    cost_usd: float
    model: str


class GateResult(BaseModel):
    """All agent responses at one gate, plus the aggregated outcome."""
    model_config = ConfigDict(extra="forbid")

    gate: GateStage
    agent_responses: list[AgentResponse]
    outcome: GateOutcome


class ScenarioRun(BaseModel):
    """The complete record of running one scenario through the simulator.

    This is the unit of data the L2-L5 scorers operate on, and the unit
    report.py aggregates across the 25-scenario suite.
    """
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    run_id: str  # uuid; lets you run N times for stochasticity
    started_at: datetime
    finished_at: datetime
    gate_results: list[GateResult]
    final_outcome: GateOutcome
    usage: list[TokenUsage]  # one per agent call; totals computed in report.py
    schema_failures: int = Field(
        default=0,
        description="Count of agent calls whose raw output failed Pydantic parse, even after retry. Feeds L1.",
    )


# --------------------------------------------------------------------------- #
# Judge output (Layer 4): the persona judge returns one of these per call.
# --------------------------------------------------------------------------- #

class PersonaVerdict(str, Enum):
    IN_PERSONA = "in_persona"
    PARTIAL = "partial"
    OUT_OF_PERSONA = "out_of_persona"


class PersonaJudgement(BaseModel):
    """Output of the L4 LLM-as-judge call. Discrete categorical, never numeric."""
    model_config = ConfigDict(extra="forbid")

    verdict: PersonaVerdict
    justification: str = Field(..., min_length=10, max_length=400)
