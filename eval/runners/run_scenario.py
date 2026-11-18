"""run_scenario.py — Phase 1 runner.

Loads a YAML scenario, runs the stakeholder agents concurrently at the
scenario's current gate, aggregates into a ScenarioRun, writes the result as JSON.

V2: grammar-constrained structured outputs (output_config json_schema) narrowed
to catalog defect IDs; one retry, with each failed attempt recorded by cause.
V1 results (JSON-in-prompt) remain in eval/runs/ for comparison.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python -m eval.runners.run_scenario eval/scenarios/scn_001_pii_logging.yaml

Output:
    eval/runs/{scenario_id}__{run_id}.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from typing import Literal

import yaml
from anthropic import Anthropic, transform_schema
from pydantic import Field, ValidationError, create_model

from dotenv import load_dotenv
load_dotenv()

from core_engine.schemas import (
    AgentResponse,
    AgentRole,
    GateDecision,
    GateOutcome,
    GateResult,
    RaisedConcern,
    Scenario,
    ScenarioRun,
    TokenUsage,
)


# --- Configuration --------------------------------------------------------- #

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096

# Anthropic Sonnet pricing per million tokens (USD). Verify on anthropic.com
# and update as needed; pricing changes break your cost numbers silently.
INPUT_PRICE_PER_MTOK = 3.0
OUTPUT_PRICE_PER_MTOK = 15.0

DEFECT_CATALOG_PATH = Path(__file__).resolve().parents[2] / "eval" / "defect_catalog.yaml"


# --- Personas (deliberately plain for the V1 baseline) --------------------- #

AGENT_PERSONAS: dict[AgentRole, str] = {
    AgentRole.PM: (
        "You are a senior Product Manager reviewing this project at a lifecycle gate. "
        "You care about: measurable acceptance criteria, well-scoped releases, honest "
        "timeline and dependency assessment, and whether the project's success can "
        "actually be evaluated. You do not write code or evaluate legal or security "
        "risk in detail. Stay in your lane."
    ),
    AgentRole.ENGINEERING_LEAD: (
        "You are a Senior Engineering Lead reviewing this project at a lifecycle gate. "
        "You care about: architectural soundness, dependency management, reliability "
        "patterns (timeouts, retries, circuit breakers), data flow correctness, and "
        "operational maturity. You do not own legal, finance, or pure product scope."
    ),
    AgentRole.SECURITY_PRIVACY: (
        "You are a Security and Privacy Reviewer at a lifecycle gate. "
        "You care about: PII handling, encryption, access control, data residency and "
        "regulatory exposure (GDPR, PCI-DSS), audit logging, and secrets management. "
        "You do not evaluate timelines, costs, or feature scope."
    ),
    AgentRole.FINOPS_LEGAL: (
        "You are a FinOps and Legal Reviewer at a lifecycle gate. "
        "You care about: cost ceilings and unit economics, vendor contracts and SLAs, "
        "regulatory compliance, license terms, and unbounded resource exposure. You "
        "do not evaluate engineering implementation details or product acceptance criteria."
    ),
}


# --- Prompt construction --------------------------------------------------- #

def load_defect_catalog() -> list[dict[str, str]]:
    if not DEFECT_CATALOG_PATH.exists():
        return []
    return yaml.safe_load(DEFECT_CATALOG_PATH.read_text()) or []


def build_user_prompt(scenario: Scenario, agent: AgentRole, catalog: list[dict]) -> str:
    catalog_lines = "\n".join(f"  - {d['id']}: {d['description']}" for d in catalog)
    project_dict = scenario.project_state.model_dump(mode="json")
    return f"""You are reviewing this project at the {scenario.project_state.stage.value}.

PROJECT STATE:
{json.dumps(project_dict, indent=2)}

KNOWN DEFECT CATALOG (use these IDs if a concern matches one; otherwise set defect_id to null):
{catalog_lines or "  (catalog empty)"}"""


# --- Output schema --------------------------------------------------------- #

def build_output_model(agent: AgentRole, gate: str, catalog: list[dict]) -> type[AgentResponse]:
    """Narrow AgentResponse so the decoding grammar admits only this agent, this gate,
    and catalog defect IDs; an ID outside the catalog cannot be generated."""
    defect_ids = Enum("DefectId", {d["id"]: d["id"] for d in catalog}, type=str)
    concern = create_model(
        "CatalogConcern",
        __base__=RaisedConcern,
        defect_id=(defect_ids | None, Field(default=None)),
    )
    return create_model(
        "CatalogAgentResponse",
        __base__=AgentResponse,
        agent=(Literal[agent.value], ...),
        gate=(Literal[gate], ...),
        concerns=(list[concern], Field(default_factory=list)),
    )


def _lowercase_enums(data: dict) -> dict:
    """Structured outputs do not guarantee enum casing; every enum value here is lowercase."""
    for key in ("agent", "gate", "decision"):
        if isinstance(data.get(key), str):
            data[key] = data[key].lower()
    for concern in data.get("concerns", []):
        for key in ("severity", "defect_id"):
            if isinstance(concern.get(key), str):
                concern[key] = concern[key].lower()
    return data


# --- Single agent call ----------------------------------------------------- #

def call_agent(
    client: Anthropic,
    agent: AgentRole,
    scenario: Scenario,
    catalog: list[dict],
) -> tuple[AgentResponse | None, TokenUsage, list[str]]:
    """Run one agent. Returns (response or None on hard failure, usage, failure causes)."""
    system_prompt = AGENT_PERSONAS[agent]
    user_prompt = build_user_prompt(scenario, agent, catalog)
    output_model = build_output_model(agent, scenario.project_state.stage.value, catalog)
    output_config = {"format": {"type": "json_schema", "schema": transform_schema(output_model)}}
    failure_causes: list[str] = []
    response: AgentResponse | None = None
    totals = {"in": 0, "out": 0, "latency_ms": 0}

    for _ in range(2):
        start = time.perf_counter()
        api_response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            output_config=output_config,
        )
        totals["latency_ms"] += int((time.perf_counter() - start) * 1000)
        totals["in"] += api_response.usage.input_tokens
        totals["out"] += api_response.usage.output_tokens

        if api_response.stop_reason in ("refusal", "max_tokens"):
            failure_causes.append(api_response.stop_reason)
            continue
        try:
            data = _lowercase_enums(json.loads(api_response.content[0].text))
            parsed = output_model.model_validate(data)
            response = AgentResponse.model_validate(parsed.model_dump(mode="json"))
            break
        except (json.JSONDecodeError, ValidationError):
            failure_causes.append("validation")

    cost = (
        totals["in"] * INPUT_PRICE_PER_MTOK / 1_000_000
        + totals["out"] * OUTPUT_PRICE_PER_MTOK / 1_000_000
    )
    usage = TokenUsage(
        prompt_tokens=totals["in"],
        completion_tokens=totals["out"],
        latency_ms=totals["latency_ms"],
        cost_usd=round(cost, 6),
        model=MODEL,
    )
    return response, usage, failure_causes


# --- Gate aggregation ------------------------------------------------------ #

def aggregate_outcome(responses: list[AgentResponse]) -> GateOutcome:
    """Simple precedence: any block wins, then any conditions, else approve."""
    decisions = {r.decision for r in responses}
    if GateDecision.BLOCK in decisions:
        return GateOutcome.BLOCKED
    if GateDecision.APPROVE_WITH_CONDITIONS in decisions:
        return GateOutcome.APPROVED_WITH_CONDITIONS
    return GateOutcome.APPROVED


# --- Main ------------------------------------------------------------------ #

def run_scenario(scenario_path: Path, output_dir: Path) -> ScenarioRun:
    scenario = Scenario.model_validate(yaml.safe_load(scenario_path.read_text()))
    catalog = load_defect_catalog()

    client = Anthropic()  # reads ANTHROPIC_API_KEY from env

    started_at = datetime.now(timezone.utc)
    responses: list[AgentResponse] = []
    usages: list[TokenUsage] = []
    failure_causes: list[str] = []

    # Sectioning: the four role reviews are independent, so they run concurrently.
    with ThreadPoolExecutor(max_workers=len(AgentRole)) as pool:
        results = list(pool.map(lambda a: (a, *call_agent(client, a, scenario, catalog)), AgentRole))

    for agent, response, usage, causes in results:
        usages.append(usage)
        failure_causes.extend(causes)
        if response is not None:
            responses.append(response)
        else:
            print(f"  WARN: {agent.value} produced no valid response after retry", file=sys.stderr)

    finished_at = datetime.now(timezone.utc)
    outcome = aggregate_outcome(responses) if responses else GateOutcome.BLOCKED

    gate_result = GateResult(
        gate=scenario.project_state.stage,
        agent_responses=responses,
        outcome=outcome,
    )

    run = ScenarioRun(
        scenario_id=scenario.id,
        run_id=str(uuid.uuid4()),
        started_at=started_at,
        finished_at=finished_at,
        gate_results=[gate_result],
        final_outcome=outcome,
        usage=usages,
        schema_failures=len(failure_causes),
        schema_failure_causes=failure_causes,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{scenario.id}__{run.run_id}.json"
    out_path.write_text(run.model_dump_json(indent=2), encoding="utf-8")

    return run


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", type=Path, help="Path to scenario YAML")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("eval/runs"),
        help="Directory to write run JSON",
    )
    args = parser.parse_args()

    if not args.scenario.exists():
        print(f"scenario not found: {args.scenario}", file=sys.stderr)
        return 1
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set", file=sys.stderr)
        return 1

    run = run_scenario(args.scenario, args.output_dir)
    total_cost = sum(u.cost_usd for u in run.usage)
    print(f"scenario:        {run.scenario_id}")
    print(f"outcome:         {run.final_outcome.value}")
    print(f"schema failures: {run.schema_failures}")
    print(f"total cost:      ${total_cost:.4f}")
    print(f"wrote:           {args.output_dir}/{run.scenario_id}__{run.run_id}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
