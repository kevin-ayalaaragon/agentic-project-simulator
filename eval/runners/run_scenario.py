"""run_scenario.py — Phase 1 runner.

Loads a YAML scenario, runs each stakeholder agent at the scenario's current
gate, parses responses through Pydantic with one retry, aggregates into a
ScenarioRun, writes the result as JSON.

Baseline (V1): raw JSON-in-prompt, no tool use, no retrieval. This is
intentionally weak so Phase 2/3 optimizations have measurable impact.

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

import yaml
from anthropic import Anthropic
from pydantic import ValidationError

from dotenv import load_dotenv
load_dotenv()

from core_engine.schemas import (
    AgentResponse,
    AgentRole,
    GateDecision,
    GateOutcome,
    GateResult,
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
{catalog_lines or "  (catalog empty)"}

Return a JSON object with this exact shape:
{{
  "agent": "{agent.value}",
  "gate": "{scenario.project_state.stage.value}",
  "decision": "approve" | "block" | "approve_with_conditions",
  "concerns": [
    {{
      "defect_id": "<catalog id or null>",
      "severity": "low" | "medium" | "high" | "blocking",
      "concern_text": "<10 to 600 chars>",
      "references": []
    }}
  ],
  "reasoning": "<20 to 1500 chars summarizing your overall assessment>"
}}

Return ONLY the JSON object. No prose, no markdown fences."""


# --- Single agent call ----------------------------------------------------- #

def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def call_agent(
    client: Anthropic,
    agent: AgentRole,
    scenario: Scenario,
    catalog: list[dict],
) -> tuple[AgentResponse | None, TokenUsage, int]:
    """Run one agent. Returns (response or None on hard failure, usage, schema_failure_count)."""
    system_prompt = AGENT_PERSONAS[agent]
    user_prompt = build_user_prompt(scenario, agent, catalog)
    schema_failures = 0
    response: AgentResponse | None = None
    totals = {"in": 0, "out": 0, "latency_ms": 0}

    for attempt in range(2):
        start = time.perf_counter()
        api_response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        totals["latency_ms"] += int((time.perf_counter() - start) * 1000)
        totals["in"] += api_response.usage.input_tokens
        totals["out"] += api_response.usage.output_tokens

        raw = _strip_fences(api_response.content[0].text)
        try:
            response = AgentResponse.model_validate(json.loads(raw))
            break
        except (json.JSONDecodeError, ValidationError):
            schema_failures += 1
            if attempt == 0:
                user_prompt += (
                    "\n\nYour previous response was not valid JSON or did not match the "
                    "schema. Return ONLY a valid JSON object exactly matching the schema above."
                )

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
    return response, usage, schema_failures


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
    schema_failures_total = 0

    for agent in AgentRole:
        response, usage, failures = call_agent(client, agent, scenario, catalog)
        usages.append(usage)
        schema_failures_total += failures
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
        schema_failures=schema_failures_total,
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
