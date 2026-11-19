"""Recompute the V2 Results table from the trial runs in eval/trials/.

Each configuration folder holds one subfolder per trial (t1, t2, ...), each
with one run JSON per scenario. Recall differences are paired by scenario and
bootstrapped over scenarios that seed defects, because trials of one scenario
are not independent. The bootstrap seed is fixed, so output is reproducible.

Usage:
    python -m eval.compare_trials
    python -m eval.compare_trials --baseline v1 --configs v1 v2_initial v2
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
from pathlib import Path

import yaml

from eval.metrics.defects import score_l2
from eval.report import latest_runs_per_scenario

AGENTS_PER_RUN = 4
BOOTSTRAP_SAMPLES = 10_000
SEED = 0


def load_trials(config_dir: Path) -> list[list[dict]]:
    """Return one list of run dicts per trial folder, in trial order."""
    trials = []
    for trial_dir in sorted(p for p in config_dir.iterdir() if p.is_dir()):
        paths = latest_runs_per_scenario(trial_dir)
        trials.append([json.loads(p.read_text(encoding="utf-8")) | {"_path": p} for p in paths])
    return trials


def flagged_ids(run: dict) -> set[str]:
    return {
        c["defect_id"]
        for gate in run["gate_results"]
        for resp in gate["agent_responses"]
        for c in resp["concerns"]
        if c["defect_id"]
    }


def summarize(trials: list[list[dict]], scenarios: dict[str, dict], scenarios_dir: Path) -> dict:
    runs = [r for trial in trials for r in trial]
    trial_scores = [score_l2([r["_path"] for r in trial], scenarios_dir) for trial in trials]
    per_scenario: dict[str, list[float]] = {}
    per_defect: dict[tuple[str, str], list[bool]] = {}
    for run in runs:
        seeded = [d["id"] for d in scenarios[run["scenario_id"]]["seeded_defects"]]
        if not seeded:
            continue
        found = flagged_ids(run)
        per_scenario.setdefault(run["scenario_id"], []).append(sum(d in found for d in seeded) / len(seeded))
        for d in seeded:
            per_defect.setdefault((run["scenario_id"], d), []).append(d in found)
    recalls = [s.suite_recall for s in trial_scores]
    return {
        "runs": len(runs),
        "valid": sum(len(g["agent_responses"]) for r in runs for g in r["gate_results"]),
        "retries": sum(r.get("schema_failures", 0) for r in runs),
        "recall_mean": statistics.mean(recalls),
        "recall_sd": statistics.stdev(recalls) if len(recalls) > 1 else 0.0,
        "precision": [s.suite_strict_precision for s in trial_scores],
        "all_trials_caught": sum(all(v) for v in per_defect.values()),
        "defects": len(per_defect),
        "gate_match": sum(r["final_outcome"] == scenarios[r["scenario_id"]]["expected_gate_outcome"] for r in runs),
        "latency_sum_s": statistics.mean(sum(u["latency_ms"] for u in r["usage"]) / 1000 for r in runs),
        "latency_max_s": statistics.mean(max(u["latency_ms"] for u in r["usage"]) / 1000 for r in runs),
        "cost": statistics.mean(sum(u["cost_usd"] for u in r["usage"]) for r in runs),
        "tool_calls": statistics.mean(len(u.get("tool_calls", [])) for r in runs for u in r["usage"]),
        "per_scenario": per_scenario,
    }


def paired_delta(config: dict, baseline: dict) -> tuple[float, float, float, list[float]]:
    """Mean per-scenario recall change with a 95% bootstrap interval over scenarios."""
    keys = sorted(baseline["per_scenario"])
    deltas = [statistics.mean(config["per_scenario"][k]) - statistics.mean(baseline["per_scenario"][k]) for k in keys]
    rng = random.Random(SEED)
    means = sorted(statistics.mean(rng.choices(deltas, k=len(deltas))) for _ in range(BOOTSTRAP_SAMPLES))
    lo, hi = means[int(0.025 * BOOTSTRAP_SAMPLES)], means[int(0.975 * BOOTSTRAP_SAMPLES)]
    return statistics.mean(deltas), lo, hi, deltas


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials-dir", type=Path, default=Path("eval/trials"))
    parser.add_argument("--scenarios-dir", type=Path, default=Path("eval/scenarios"))
    parser.add_argument("--baseline", default="v1")
    parser.add_argument("--configs", nargs="+", default=["v1", "v2_initial", "v2"])
    args = parser.parse_args()

    scenarios = {}
    for path in args.scenarios_dir.glob("*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        scenarios[data["id"]] = data
    results = {c: summarize(load_trials(args.trials_dir / c), scenarios, args.scenarios_dir) for c in args.configs}
    base = results[args.baseline]

    print("| Metric | " + " | ".join(args.configs) + " |")
    print("|---" * (len(args.configs) + 1) + "|")
    rows = {
        "Format pass rate": lambda r: f"{r['valid']}/{r['runs'] * AGENTS_PER_RUN}",
        "Failed attempts (retries)": lambda r: str(r["retries"]),
        "Tagged recall, mean of trials (SD)": lambda r: f"{r['recall_mean']:.2f} ({r['recall_sd']:.2f})",
        "Seeded defects caught in all trials": lambda r: f"{r['all_trials_caught']}/{r['defects']}",
        "Strict precision (per trial)": lambda r: " / ".join(f"{p:.2f}" for p in r["precision"]),
        "Gate outcome matches expected": lambda r: f"{r['gate_match']}/{r['runs']}",
        "Summed agent latency per scenario": lambda r: f"{r['latency_sum_s']:.0f} s",
        "Slowest agent latency per scenario": lambda r: f"{r['latency_max_s']:.0f} s",
        "Cost per scenario": lambda r: f"${r['cost']:.3f}",
        "Tool calls per agent": lambda r: f"{r['tool_calls']:.1f}",
    }
    for name, fmt in rows.items():
        print(f"| {name} | " + " | ".join(fmt(results[c]) for c in args.configs) + " |")

    print(f"\nRecall change vs {args.baseline}, paired by scenario (95% bootstrap CI, seed {SEED}):")
    for c in args.configs:
        if c == args.baseline:
            continue
        mean, lo, hi, deltas = paired_delta(results[c], base)
        print(f"  {c}: {mean:+.3f} [{lo:+.3f}, {hi:+.3f}]  per scenario: {[round(d, 2) for d in deltas]}")
    print("\nSequential runs take the summed latency; parallel runs take the slowest agent's.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
