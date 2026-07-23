"""L4: Persona-fidelity judge.

Scores whether a single raised concern falls inside the domain of the agent
that raised it. Discrete categorical verdict, never a numeric scale, because
numeric scales drift between runs.

Blind by construction. The judge sees only the agent's role definition and the
concern text. It never sees defect_id, severity, whether the concern matched a
seeded defect, the agent's own summary reasoning, or the scenario's expected
outcome. Any of those would leak signal into a judgement that is supposed to be
about scope alone.

The judge runs on a different model from the agents to avoid self-preference
bias, where a model scores outputs from its own family generously.

Role definitions are imported from the runner rather than copied, so the judge
always scores against the personas the agents were actually given.
"""

from __future__ import annotations

import json
import time

from anthropic import Anthropic
from pydantic import ValidationError

from core_engine.schemas import AgentRole, PersonaJudgement, TokenUsage
from eval.runners.run_scenario import AGENT_PERSONAS


# --- Configuration --------------------------------------------------------- #

# MUST differ from the agent model (claude-sonnet-4-6) to avoid self-preference
# bias. Verify this string is available on your account before a full run.
JUDGE_MODEL = "claude-opus-4-8"
JUDGE_MAX_TOKENS = 512

# Some models reject the temperature parameter entirely. Leave as None for those.
# Set to 0.0 only if the judge model accepts it, which makes a single judging pass
# reproducible. When it is None, L4 numbers are stochastic and should be reported
# as a mean plus spread across repeated runs rather than as a single figure.
JUDGE_TEMPERATURE: float | None = None

# Judge-model pricing per million tokens (USD). Verify on anthropic.com and
# update as needed; pricing changes break your cost numbers silently.
JUDGE_INPUT_PRICE_PER_MTOK = 15.0
JUDGE_OUTPUT_PRICE_PER_MTOK = 75.0


RUBRIC = """You are evaluating whether a single review concern falls inside the domain of the reviewer who raised it.

You are judging SCOPE ONLY. A concern can be accurate, important, and well argued and still fall outside the reviewer's domain. Whether the concern is correct is not your question. Do not reward or penalize it for quality, severity, or whether you agree with it.

Verdicts:
- "in_persona": the concern falls squarely inside the reviewer's stated domain.
- "partial": the concern is anchored in the reviewer's domain but reaches materially into another reviewer's domain, or is framed primarily in another domain's terms.
- "out_of_persona": the concern falls primarily inside another reviewer's domain, including any domain the reviewer is explicitly told they do not own.

When the verdict is "partial" or "out_of_persona", set "encroaches_on" to the single role whose domain the concern most reaches into. When the verdict is "in_persona", set it to null.

Valid values for "encroaches_on": "pm_agent", "engineering_lead_agent", "security_privacy_agent", "finops_legal_agent", or null.

Return ONLY a JSON object with this exact shape. No prose, no markdown fences:
{
  "verdict": "in_persona" | "partial" | "out_of_persona",
  "encroaches_on": "<role or null>",
  "justification": "<10 to 400 chars explaining the scope call>"
}"""


def build_judge_prompt(agent: AgentRole, concern_text: str) -> str:
    """Blind prompt: role definition plus concern text, nothing else."""
    return f"""REVIEWER ROLE DEFINITION:
{AGENT_PERSONAS[agent]}

CONCERN RAISED BY THIS REVIEWER:
{concern_text}"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def judge_concern(
    client: Anthropic,
    agent: AgentRole,
    concern_text: str,
    model: str = JUDGE_MODEL,
) -> tuple[PersonaJudgement | None, TokenUsage, int]:
    """Judge one concern. Returns (judgement or None, usage, schema_failure_count).

    Mirrors the runner's one-retry policy so L1-style schema discipline applies
    to the judge itself.
    """
    user_prompt = build_judge_prompt(agent, concern_text)
    schema_failures = 0
    judgement: PersonaJudgement | None = None
    totals = {"in": 0, "out": 0, "latency_ms": 0}

    for attempt in range(2):
        start = time.perf_counter()
        call_kwargs: dict = {
            "model": model,
            "max_tokens": JUDGE_MAX_TOKENS,
            "system": RUBRIC,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        if JUDGE_TEMPERATURE is not None:
            call_kwargs["temperature"] = JUDGE_TEMPERATURE
        api_response = client.messages.create(**call_kwargs)
        totals["latency_ms"] += int((time.perf_counter() - start) * 1000)
        totals["in"] += api_response.usage.input_tokens
        totals["out"] += api_response.usage.output_tokens

        raw = _strip_fences(api_response.content[0].text)
        try:
            judgement = PersonaJudgement.model_validate(json.loads(raw))
            break
        except (json.JSONDecodeError, ValidationError):
            schema_failures += 1
            if attempt == 0:
                user_prompt += (
                    "\n\nYour previous response was not valid JSON or did not match the "
                    "schema. Return ONLY a valid JSON object exactly matching the schema."
                )

    cost = (
        totals["in"] * JUDGE_INPUT_PRICE_PER_MTOK / 1_000_000
        + totals["out"] * JUDGE_OUTPUT_PRICE_PER_MTOK / 1_000_000
    )
    usage = TokenUsage(
        prompt_tokens=totals["in"],
        completion_tokens=totals["out"],
        latency_ms=totals["latency_ms"],
        cost_usd=round(cost, 6),
        model=model,
    )
    return judgement, usage, schema_failures
