"""L1: Schema validity scorer.

For the V1 baseline, this measures whether the agent returned a parseable,
schema-compliant response. The runner already enforces validation with one
retry; we measure two related signals from its output:

  - format_pass_rate = valid_responses / expected_responses
    "Did we end up with a parseable response from every agent we called?"
  - retries_used: the raw count of failed attempts the runner needed
    "How shaky is the raw model output before the retry crutch?"

In V2, tool-use enforcement should drive pass_rate to 100% and retries to 0.
The retry count is the more sensitive metric and the one V2 should move most.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

EXPECTED_AGENTS_PER_RUN = 4


@dataclass
class L1Result:
    runs: int
    expected_responses: int
    valid_responses: int
    retries_used: int
    pass_rate: float


def score_l1(run_paths: list[Path]) -> L1Result:
    expected = 0
    valid = 0
    retries = 0
    for path in run_paths:
        run = json.loads(path.read_text(encoding="utf-8"))
        expected += EXPECTED_AGENTS_PER_RUN
        valid += sum(len(gr["agent_responses"]) for gr in run["gate_results"])
        retries += run.get("schema_failures", 0)
    return L1Result(
        runs=len(run_paths),
        expected_responses=expected,
        valid_responses=valid,
        retries_used=retries,
        pass_rate=(valid / expected) if expected else 0.0,
    )
