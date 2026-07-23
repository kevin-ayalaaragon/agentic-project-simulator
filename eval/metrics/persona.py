"""L4 scorer: runs the persona judge across all concerns and aggregates.

Produces:
  - in-persona rate, overall and per agent
  - an encroachment cross-tab (which agent reaches into which domain)
  - a partition of L2's unmatched flags into persona drift vs plausible
    legitimate unseeded catches, which decomposes the strict-precision floor

Writes per-scenario verdict files to eval/runs_persona/ as it goes, so a long
run is resumable and a crash costs at most one scenario.

Usage:
    python -m eval.metrics.persona
    python -m eval.metrics.persona --force   # re-judge scenarios already done
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from anthropic import Anthropic

from core_engine.schemas import AgentRole, PersonaVerdict
from eval.judges.persona_judge import JUDGE_MODEL, judge_concern


@dataclass
class ConcernVerdict:
    scenario_id: str
    agent: str
    concern_index: int
    concern_text: str
    verdict: str
    encroaches_on: str | None
    justification: str
    matched_seeded_defect: bool


@dataclass
class L4Result:
    verdicts: list[ConcernVerdict]
    in_persona_rate: float
    per_agent_rate: dict[str, float] = field(default_factory=dict)
    encroachment: dict[str, dict[str, int]] = field(default_factory=dict)
    unmatched_partition: dict[str, int] = field(default_factory=dict)
    total_cost_usd: float = 0.0
    judge_schema_failures: int = 0


def latest_runs_per_scenario(runs_dir: Path) -> list[Path]:
    """Most recent run JSON per scenario_id. Mirrors report.py."""
    by_scenario: dict[str, tuple[str, Path]] = {}
    for path in sorted(runs_dir.glob("*.json")):
        try:
            run = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"  WARN: could not parse {path.name}, skipping", file=sys.stderr)
            continue
        sid = run.get("scenario_id", "")
        if not sid:
            continue
        finished_at = run.get("finished_at", "")
        if sid not in by_scenario or finished_at > by_scenario[sid][0]:
            by_scenario[sid] = (finished_at, path)
    return [p for _, p in by_scenario.values()]


def _seeded_ids(scenarios_dir: Path, scenario_id: str) -> set[str]:
    path = scenarios_dir / f"{scenario_id}.yaml"
    if not path.exists():
        return set()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {d["id"] for d in data.get("seeded_defects", [])}


def judge_run(
    client: Anthropic,
    run_path: Path,
    scenarios_dir: Path,
    out_dir: Path,
    model: str,
    force: bool,
) -> tuple[list[ConcernVerdict], float, int]:
    run = json.loads(run_path.read_text(encoding="utf-8"))
    scenario_id = run["scenario_id"]
    out_path = out_dir / f"{scenario_id}.json"

    if out_path.exists() and not force:
        cached = json.loads(out_path.read_text(encoding="utf-8"))
        return (
            [ConcernVerdict(**v) for v in cached["verdicts"]],
            cached.get("cost_usd", 0.0),
            cached.get("schema_failures", 0),
        )

    seeded = _seeded_ids(scenarios_dir, scenario_id)
    verdicts: list[ConcernVerdict] = []
    cost = 0.0
    failures = 0

    for gate in run["gate_results"]:
        for response in gate["agent_responses"]:
            agent = response["agent"]
            for idx, concern in enumerate(response["concerns"]):
                text = concern.get("concern_text", "")
                judgement, usage, fails = judge_concern(
                    client, AgentRole(agent), text, model=model
                )
                cost += usage.cost_usd
                failures += fails
                if judgement is None:
                    print(
                        f"  WARN: judge produced no valid verdict for "
                        f"{scenario_id}/{agent}/{idx}",
                        file=sys.stderr,
                    )
                    continue
                defect_id = concern.get("defect_id")
                verdicts.append(ConcernVerdict(
                    scenario_id=scenario_id,
                    agent=agent,
                    concern_index=idx,
                    concern_text=text,
                    verdict=judgement.verdict.value,
                    encroaches_on=(
                        judgement.encroaches_on.value if judgement.encroaches_on else None
                    ),
                    justification=judgement.justification,
                    matched_seeded_defect=bool(defect_id and defect_id in seeded),
                ))

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "scenario_id": scenario_id,
        "judge_model": model,
        "cost_usd": round(cost, 6),
        "schema_failures": failures,
        "verdicts": [v.__dict__ for v in verdicts],
    }, indent=2), encoding="utf-8")

    return verdicts, cost, failures


def aggregate(verdicts: list[ConcernVerdict]) -> L4Result:
    total = len(verdicts)
    in_persona = sum(1 for v in verdicts if v.verdict == PersonaVerdict.IN_PERSONA.value)

    per_agent_total: collections.Counter[str] = collections.Counter()
    per_agent_in: collections.Counter[str] = collections.Counter()
    encroachment: dict[str, dict[str, int]] = collections.defaultdict(
        lambda: collections.defaultdict(int)
    )
    partition: collections.Counter[str] = collections.Counter()

    for v in verdicts:
        per_agent_total[v.agent] += 1
        if v.verdict == PersonaVerdict.IN_PERSONA.value:
            per_agent_in[v.agent] += 1
        if v.encroaches_on:
            encroachment[v.agent][v.encroaches_on] += 1
        if not v.matched_seeded_defect:
            if v.verdict == PersonaVerdict.IN_PERSONA.value:
                partition["in_persona_unseeded_catch"] += 1
            elif v.verdict == PersonaVerdict.PARTIAL.value:
                partition["partial"] += 1
            else:
                partition["persona_drift"] += 1

    return L4Result(
        verdicts=verdicts,
        in_persona_rate=(in_persona / total) if total else 0.0,
        per_agent_rate={
            a: per_agent_in[a] / per_agent_total[a] for a in sorted(per_agent_total)
        },
        encroachment={a: dict(d) for a, d in encroachment.items()},
        unmatched_partition=dict(partition),
    )


def score_l4(
    runs_dir: Path,
    scenarios_dir: Path,
    out_dir: Path,
    model: str = JUDGE_MODEL,
    force: bool = False,
) -> L4Result:
    client = Anthropic()
    all_verdicts: list[ConcernVerdict] = []
    total_cost = 0.0
    total_failures = 0

    run_paths = latest_runs_per_scenario(runs_dir)
    for i, path in enumerate(run_paths, 1):
        print(f"[{i}/{len(run_paths)}] judging {path.name}", file=sys.stderr)
        verdicts, cost, failures = judge_run(
            client, path, scenarios_dir, out_dir, model, force
        )
        all_verdicts.extend(verdicts)
        total_cost += cost
        total_failures += failures

    result = aggregate(all_verdicts)
    result.total_cost_usd = round(total_cost, 4)
    result.judge_schema_failures = total_failures
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-dir", type=Path, default=Path("eval/runs"))
    parser.add_argument("--scenarios-dir", type=Path, default=Path("eval/scenarios"))
    parser.add_argument("--out-dir", type=Path, default=Path("eval/runs_persona"))
    parser.add_argument("--judge-model", type=str, default=JUDGE_MODEL)
    parser.add_argument("--force", action="store_true", help="re-judge cached scenarios")
    args = parser.parse_args()

    if not args.runs_dir.exists():
        print(f"runs dir not found: {args.runs_dir}", file=sys.stderr)
        return 1

    result = score_l4(
        args.runs_dir, args.scenarios_dir, args.out_dir, args.judge_model, args.force
    )

    print()
    print(f"judge model:            {args.judge_model}")
    print(f"concerns judged:        {len(result.verdicts)}")
    print(f"judge schema failures:  {result.judge_schema_failures}")
    print(f"judging cost:           ${result.total_cost_usd:.4f}")
    print(f"in-persona rate:        {result.in_persona_rate:.2f}")
    print()
    print("per agent:")
    for agent, rate in result.per_agent_rate.items():
        print(f"  {agent:28s} {rate:.2f}")
    print()
    print("encroachment (raiser -> domain reached into):")
    for agent, targets in sorted(result.encroachment.items()):
        for target, n in sorted(targets.items(), key=lambda kv: -kv[1]):
            print(f"  {agent:28s} -> {target:28s} {n}")
    print()
    print("unmatched-flag partition:")
    for k, n in sorted(result.unmatched_partition.items(), key=lambda kv: -kv[1]):
        print(f"  {k:32s} {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
