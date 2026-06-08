"""Aggregates L1 + L2 scores into a markdown report.

- Dedupes stale runs: keeps the most recent run per scenario_id (by finished_at).
- Writes the populated master table and the unmatched-flag triage list to
  a single markdown file you can commit or paste into the README.
- Prints the summary block to stdout.

Usage:
    python -m eval.report
    python -m eval.report --runs-dir eval/runs --scenarios-dir eval/scenarios --out eval/report.md
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from eval.metrics.schema import score_l1
from eval.metrics.defects import score_l2


def latest_runs_per_scenario(runs_dir: Path) -> list[Path]:
    """Return the most recent run JSON per scenario_id."""
    by_scenario: dict[str, tuple[str, Path]] = {}
    for path in sorted(runs_dir.glob("*.json")):
        try:
            run = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"  WARN: could not parse {path.name}, skipping", file=sys.stderr)
            continue
        sid = run.get("scenario_id", "")
        finished_at = run.get("finished_at", "")
        if not sid:
            continue
        if sid not in by_scenario or finished_at > by_scenario[sid][0]:
            by_scenario[sid] = (finished_at, path)
    return [p for _, p in by_scenario.values()]


def build_report(runs_dir: Path, scenarios_dir: Path) -> str:
    run_paths = latest_runs_per_scenario(runs_dir)
    l1 = score_l1(run_paths)
    l2 = score_l2(run_paths, scenarios_dir)

    lines: list[str] = []
    lines.append("# Eval Report (V1 Baseline)")
    lines.append(f"_Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}_")
    lines.append(f"_Scenarios scored: {l1.runs}_")
    lines.append("")

    lines.append("## Master Table")
    lines.append("")
    lines.append("| Pillar | Metric | V1 Baseline |")
    lines.append("|--------|--------|-------------|")
    lines.append(
        f"| Structural | Format pass rate | "
        f"{l1.pass_rate:.0%} ({l1.valid_responses}/{l1.expected_responses}) "
        f"(retries used: {l1.retries_used}) |"
    )
    lines.append(f"| Functional | Defect-detection recall (suite mean) | {l2.suite_recall:.2f} |")
    lines.append(
        f"| Functional | Defect-detection strict precision (suite mean) | "
        f"{l2.suite_strict_precision:.2f} |"
    )
    lines.append("")

    lines.append("## Per-Scenario L2")
    lines.append("")
    lines.append("| Scenario | Seeded | Caught | Recall | Flags | Matched | Strict Precision |")
    lines.append("|----------|--------|--------|--------|-------|---------|------------------|")
    for s in l2.per_scenario:
        lines.append(
            f"| {s.scenario_id} | {s.seeded_count} | {s.caught_count} | "
            f"{s.recall:.2f} | {s.total_flags} | {s.matched_flags} | "
            f"{s.strict_precision:.2f} |"
        )
    lines.append("")

    lines.append(f"## Unmatched Flags ({len(l2.all_unmatched)} total)")
    lines.append("")
    lines.append("These concerns did not match any seeded defect ID. Triage each:")
    lines.append("")
    lines.append("- **Real but unseeded**: the agent caught a legitimate issue you didn't seed. ")
    lines.append("  Add it to the scenario's `seeded_defects` so recall and precision both improve.")
    lines.append("- **Noise**: the agent over-flagged. Counts as a true false positive.")
    lines.append("- **Catalog typo**: the agent malformed a defect ID (e.g. `def_def_pii_in_logs`). ")
    lines.append("  This is a V1 schema-discipline failure; tool-use enforcement in V2 prevents it.")
    lines.append("")
    for uf in l2.all_unmatched:
        snippet = uf.concern_text[:200] + ("..." if len(uf.concern_text) > 200 else "")
        lines.append(
            f"- **{uf.scenario_id}** / {uf.agent} / "
            f"`{uf.defect_id}` / {uf.severity}"
        )
        lines.append(f"  > {snippet}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-dir", type=Path, default=Path("eval/runs"))
    parser.add_argument("--scenarios-dir", type=Path, default=Path("eval/scenarios"))
    parser.add_argument("--out", type=Path, default=Path("eval/report.md"))
    args = parser.parse_args()

    if not args.runs_dir.exists():
        print(f"runs dir not found: {args.runs_dir}", file=sys.stderr)
        return 1
    if not args.scenarios_dir.exists():
        print(f"scenarios dir not found: {args.scenarios_dir}", file=sys.stderr)
        return 1

    report = build_report(args.runs_dir, args.scenarios_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")

    # Print the summary block (everything up to per-scenario detail)
    print(report.split("## Per-Scenario L2")[0])
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
