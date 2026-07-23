"""Judge validation: agreement between the L4 judge and human labels.

Reports raw agreement, Cohen's kappa, and linearly weighted kappa. Raw
agreement alone is chance-inflated and misleading on a skewed distribution;
kappa corrects for agreement expected by chance. The categories are ordered
(in_persona < partial < out_of_persona), so weighted kappa is also reported,
since confusing adjacent categories should cost less than confusing the
extremes.

Implemented without numpy or sklearn to avoid adding dependencies.

Usage:
    python -m eval.judges.judge_validation.score_agreement
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from core_engine.schemas import PersonaVerdict

CATEGORIES = [v.value for v in PersonaVerdict]  # ordered: in, partial, out
INDEX = {c: i for i, c in enumerate(CATEGORIES)}


def confusion_matrix(pairs: list[tuple[str, str]]) -> list[list[int]]:
    k = len(CATEGORIES)
    m = [[0] * k for _ in range(k)]
    for human, model in pairs:
        m[INDEX[human]][INDEX[model]] += 1
    return m


def _marginals(m: list[list[int]]) -> tuple[list[int], list[int], int]:
    rows = [sum(r) for r in m]
    cols = [sum(m[i][j] for i in range(len(m))) for j in range(len(m[0]))]
    return rows, cols, sum(rows)


def cohens_kappa(m: list[list[int]], weighted: bool = False) -> float:
    rows, cols, n = _marginals(m)
    if n == 0:
        return 0.0
    k = len(CATEGORIES)

    def weight(i: int, j: int) -> float:
        if not weighted:
            return 1.0 if i == j else 0.0
        return 1.0 - abs(i - j) / (k - 1)

    po = sum(weight(i, j) * m[i][j] for i in range(k) for j in range(k)) / n
    pe = sum(
        weight(i, j) * rows[i] * cols[j] / n for i in range(k) for j in range(k)
    ) / n
    if pe == 1.0:
        return 0.0
    return (po - pe) / (1 - pe)


def interpret(kappa: float) -> str:
    if kappa < 0.0:
        return "worse than chance"
    if kappa < 0.20:
        return "slight"
    if kappa < 0.40:
        return "fair"
    if kappa < 0.60:
        return "moderate"
    if kappa < 0.80:
        return "substantial"
    return "almost perfect"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dir", type=Path, default=Path("eval/judges/judge_validation")
    )
    args = parser.parse_args()

    labels_path = args.dir / "sample_to_label.csv"
    key_path = args.dir / "sample_key.json"
    if not labels_path.exists() or not key_path.exists():
        print(f"missing {labels_path} or {key_path}", file=sys.stderr)
        return 1

    key = {row["sample_id"]: row for row in json.loads(key_path.read_text(encoding="utf-8"))}

    pairs: list[tuple[str, str]] = []
    unlabeled = 0
    invalid = 0
    with labels_path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            human = (row.get("human_verdict") or "").strip()
            if not human:
                unlabeled += 1
                continue
            if human not in INDEX:
                print(f"  WARN: invalid verdict '{human}' at sample {row['sample_id']}",
                      file=sys.stderr)
                invalid += 1
                continue
            model = key[int(row["sample_id"])]["model_verdict"]
            pairs.append((human, model))

    if not pairs:
        print("no labeled rows found", file=sys.stderr)
        return 1

    m = confusion_matrix(pairs)
    rows, cols, n = _marginals(m)
    raw = sum(m[i][i] for i in range(len(CATEGORIES))) / n
    kappa = cohens_kappa(m)
    weighted = cohens_kappa(m, weighted=True)

    print(f"labeled samples:        {n}")
    if unlabeled:
        print(f"unlabeled (skipped):    {unlabeled}")
    if invalid:
        print(f"invalid (skipped):      {invalid}")
    print(f"raw agreement:          {raw:.2f}")
    print(f"Cohen's kappa:          {kappa:.2f}  ({interpret(kappa)})")
    print(f"weighted kappa (linear):{weighted:.2f}  ({interpret(weighted)})")
    print()
    header = "human \\ model".ljust(18) + "".join(c.ljust(18) for c in CATEGORIES)
    print(header)
    for i, c in enumerate(CATEGORIES):
        print(c.ljust(18) + "".join(str(m[i][j]).ljust(18) for j in range(len(CATEGORIES))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
