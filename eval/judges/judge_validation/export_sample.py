"""Export a stratified validation sample for blind hand-labeling.

Stratified rather than random: a random draw from a skewed pool can contain
zero out-of-persona examples, which makes kappa undefined or wildly unstable.
Sampling across the judge's predicted categories validates agreement at the
decision boundary, which is what the metric is for.

The exported CSV deliberately does NOT contain the judge's verdict. Labeling
while able to see the model's answer measures anchoring, not agreement. The
verdicts are written to a separate key file, joined only at scoring time.

Usage:
    python -m eval.judges.judge_validation.export_sample
    python -m eval.judges.judge_validation.export_sample --per-category 15
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

from core_engine.schemas import PersonaVerdict

CATEGORIES = [v.value for v in PersonaVerdict]


def load_verdicts(persona_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(persona_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        rows.extend(data.get("verdicts", []))
    return rows


def stratified_sample(rows: list[dict], per_category: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    sample: list[dict] = []
    for category in CATEGORIES:
        pool = [r for r in rows if r["verdict"] == category]
        rng.shuffle(pool)
        take = pool[:per_category]
        if len(take) < per_category:
            print(
                f"  NOTE: only {len(take)} available for '{category}' "
                f"(requested {per_category})",
                file=sys.stderr,
            )
        sample.extend(take)
    rng.shuffle(sample)  # present in random order so category is not guessable
    return sample


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--persona-dir", type=Path, default=Path("eval/runs_persona"))
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("eval/judges/judge_validation"),
    )
    parser.add_argument("--per-category", type=int, default=15)
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()

    if not args.persona_dir.exists():
        print(f"persona dir not found: {args.persona_dir}", file=sys.stderr)
        print("run: python -m eval.metrics.persona", file=sys.stderr)
        return 1

    rows = load_verdicts(args.persona_dir)
    if not rows:
        print("no verdicts found", file=sys.stderr)
        return 1

    sample = stratified_sample(rows, args.per_category, args.seed)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    labels_path = args.out_dir / "sample_to_label.csv"
    key_path = args.out_dir / "sample_key.json"

    with labels_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "sample_id", "agent", "concern_text",
            "human_verdict", "human_encroaches_on", "notes",
        ])
        for i, row in enumerate(sample):
            writer.writerow([i, row["agent"], row["concern_text"], "", "", ""])

    key_path.write_text(json.dumps([
        {
            "sample_id": i,
            "scenario_id": row["scenario_id"],
            "agent": row["agent"],
            "concern_index": row["concern_index"],
            "model_verdict": row["verdict"],
            "model_encroaches_on": row["encroaches_on"],
        }
        for i, row in enumerate(sample)
    ], indent=2), encoding="utf-8")

    print(f"wrote {labels_path}  ({len(sample)} rows to label)")
    print(f"wrote {key_path}  (model verdicts, do not open before labeling)")
    print()
    print("Fill human_verdict with one of: " + ", ".join(CATEGORIES))
    print("Fill human_encroaches_on only for partial or out_of_persona.")
    print("Judge scope only. A concern can be correct and still be out of domain.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
