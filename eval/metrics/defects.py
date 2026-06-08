"""L2: Defect-detection scorer.

For each ScenarioRun, computes precision and recall against the seeded
defects in the matching scenario YAML.

Match policy (V1):
  A seeded defect counts as caught if ANY agent raised a concern with that
  exact defect_id. The agent role is recorded but not required to match
  `should_be_caught_by`. A stricter mode requiring the right agent is
  trivially derivable from the same data; we don't compute it by default.

Strict precision treats every unmatched flag as a false positive. That is
known to be over-pessimistic because agents legitimately catch issues we
didn't seed (see the unmatched_flags list for manual review). The reported
strict precision is the floor; the true precision is between strict and
1.0 depending on how many unmatched flags turn out to be real catches.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class UnmatchedFlag:
    scenario_id: str
    agent: str
    defect_id: str | None
    severity: str
    concern_text: str


@dataclass
class ScenarioL2:
    scenario_id: str
    seeded_count: int
    caught_count: int
    matched_flags: int
    total_flags: int
    recall: float
    strict_precision: float
    unmatched: list[UnmatchedFlag] = field(default_factory=list)


@dataclass
class L2Result:
    per_scenario: list[ScenarioL2]
    suite_recall: float            # mean over scenarios with seeded defects
    suite_strict_precision: float  # mean over scenarios with any raised flag
    all_unmatched: list[UnmatchedFlag]


def _load_scenario(scenarios_dir: Path, scenario_id: str) -> dict:
    path = scenarios_dir / f"{scenario_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"no scenario YAML at {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def score_l2(run_paths: list[Path], scenarios_dir: Path) -> L2Result:
    per_scenario: list[ScenarioL2] = []
    all_unmatched: list[UnmatchedFlag] = []

    for path in run_paths:
        run = json.loads(path.read_text(encoding="utf-8"))
        scenario_id = run["scenario_id"]
        scenario = _load_scenario(scenarios_dir, scenario_id)
        seeded_ids = {d["id"] for d in scenario.get("seeded_defects", [])}

        # Gather all raised concerns across all agents and gates.
        raised: list[tuple[str, dict]] = []
        for gate in run["gate_results"]:
            for agent in gate["agent_responses"]:
                for concern in agent["concerns"]:
                    raised.append((agent["agent"], concern))

        caught_ids: set[str] = set()
        matched_flags = 0
        unmatched: list[UnmatchedFlag] = []

        for agent_name, concern in raised:
            defect_id = concern.get("defect_id")
            if defect_id and defect_id in seeded_ids:
                caught_ids.add(defect_id)
                matched_flags += 1
            else:
                unmatched.append(UnmatchedFlag(
                    scenario_id=scenario_id,
                    agent=agent_name,
                    defect_id=defect_id,
                    severity=concern.get("severity", ""),
                    concern_text=concern.get("concern_text", ""),
                ))

        total_flags = len(raised)
        recall = (len(caught_ids) / len(seeded_ids)) if seeded_ids else 1.0
        strict_precision = (matched_flags / total_flags) if total_flags else 1.0

        per_scenario.append(ScenarioL2(
            scenario_id=scenario_id,
            seeded_count=len(seeded_ids),
            caught_count=len(caught_ids),
            matched_flags=matched_flags,
            total_flags=total_flags,
            recall=recall,
            strict_precision=strict_precision,
            unmatched=unmatched,
        ))
        all_unmatched.extend(unmatched)

    defective = [s for s in per_scenario if s.seeded_count > 0]
    flagged = [s for s in per_scenario if s.total_flags > 0]

    suite_recall = sum(s.recall for s in defective) / len(defective) if defective else 0.0
    suite_strict_precision = (
        sum(s.strict_precision for s in flagged) / len(flagged) if flagged else 0.0
    )

    return L2Result(
        per_scenario=per_scenario,
        suite_recall=suite_recall,
        suite_strict_precision=suite_strict_precision,
        all_unmatched=all_unmatched,
    )
