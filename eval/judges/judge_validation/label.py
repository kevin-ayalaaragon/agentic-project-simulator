"""Interactive blind labeler for the L4 judge validation sample.

Shows one concern at a time alongside the role definition the agent was given,
takes a single-keystroke verdict, and writes back to sample_to_label.csv after
every entry so nothing is lost if you stop partway.

Blind by construction: the judge's verdict lives in sample_key.json and is never
read by this script. Labeling while able to see the model's answer measures
anchoring, not agreement.

Usage:
    python -m eval.judges.judge_validation.label
    python -m eval.judges.judge_validation.label --review   # revisit labeled rows
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
import textwrap
from pathlib import Path

from core_engine.schemas import AgentRole, PersonaVerdict
from eval.runners.run_scenario import AGENT_PERSONAS

FIELDS = ["sample_id", "agent", "concern_text", "human_verdict",
          "human_encroaches_on", "notes"]

VERDICTS = {
    "1": PersonaVerdict.IN_PERSONA.value,
    "2": PersonaVerdict.PARTIAL.value,
    "3": PersonaVerdict.OUT_OF_PERSONA.value,
}
ROLES = {
    "1": AgentRole.PM.value,
    "2": AgentRole.ENGINEERING_LEAD.value,
    "3": AgentRole.SECURITY_PRIVACY.value,
    "4": AgentRole.FINOPS_LEGAL.value,
}


def width() -> int:
    return min(shutil.get_terminal_size((100, 24)).columns, 100)


def rule(char: str = "=") -> str:
    return char * width()


def wrap(text: str, indent: str = "") -> str:
    return textwrap.fill(
        text, width=width() - len(indent),
        initial_indent=indent, subsequent_indent=indent,
    )


def load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def save_rows(path: Path, rows: list[dict]) -> None:
    tmp = path.with_suffix(".csv.tmp")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in FIELDS})
    tmp.replace(path)


def show(row: dict, position: int, total: int, remaining: int) -> None:
    agent = row["agent"]
    print("\n" + rule())
    print(f"  sample {row['sample_id']}   ({position} of {total} shown, "
          f"{remaining} still unlabeled)")
    print(rule())
    print(f"\nREVIEWER: {agent}\n")
    try:
        print(wrap(AGENT_PERSONAS[AgentRole(agent)], indent="  "))
    except (KeyError, ValueError):
        print("  (role definition unavailable)")
    print("\n" + rule("-"))
    print("\nCONCERN RAISED:\n")
    print(wrap(row["concern_text"], indent="  "))
    print("\n" + rule("-"))
    if row.get("human_verdict"):
        print(f"  current label: {row['human_verdict']}")


def prompt_verdict() -> str | None:
    print("\n  [1] in_persona    [2] partial    [3] out_of_persona")
    print("  [k] skip   [b] back   [q] save and quit")
    while True:
        choice = input("  verdict > ").strip().lower()
        if choice in VERDICTS:
            return VERDICTS[choice]
        if choice in {"k", "b", "q"}:
            return choice
        print("  not a valid choice")


def prompt_role() -> str:
    print("\n  encroaches on which domain? (optional, Enter to skip)")
    print("  [1] pm   [2] engineering   [3] security   [4] finops")
    while True:
        choice = input("  domain > ").strip().lower()
        if choice == "":
            return ""
        if choice in ROLES:
            return ROLES[choice]
        print("  not a valid choice")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", type=Path,
                        default=Path("eval/judges/judge_validation"))
    parser.add_argument("--review", action="store_true",
                        help="revisit rows that already have a label")
    args = parser.parse_args()

    path = args.dir / "sample_to_label.csv"
    if not path.exists():
        print(f"not found: {path}", file=sys.stderr)
        print("run: python -m eval.judges.judge_validation.export_sample",
              file=sys.stderr)
        return 1

    rows = load_rows(path)
    queue = [i for i, r in enumerate(rows)
             if args.review or not r.get("human_verdict", "").strip()]

    if not queue:
        print("all rows are labeled. use --review to revisit them.")
        return 0

    print(rule())
    print("  JUDGE SCOPE, NOT CORRECTNESS.")
    print("  A concern can be accurate, important, and still be out of domain.")
    print("  Use 'partial' when a concern has a real in-domain anchor but the")
    print("  framing or substance reaches into another reviewer's territory.")
    print(rule())

    pos = 0
    while 0 <= pos < len(queue):
        idx = queue[pos]
        remaining = sum(1 for r in rows if not r.get("human_verdict", "").strip())
        show(rows[idx], pos + 1, len(queue), remaining)

        choice = prompt_verdict()
        if choice == "q":
            break
        if choice == "k":
            pos += 1
            continue
        if choice == "b":
            pos = max(0, pos - 1)
            continue

        rows[idx]["human_verdict"] = choice
        if choice != PersonaVerdict.IN_PERSONA.value:
            rows[idx]["human_encroaches_on"] = prompt_role()
        else:
            rows[idx]["human_encroaches_on"] = ""
        save_rows(path, rows)
        pos += 1

    labeled = sum(1 for r in rows if r.get("human_verdict", "").strip())
    print("\n" + rule())
    print(f"  labeled {labeled} of {len(rows)}. saved to {path}")
    if labeled < len(rows):
        print("  rerun the same command to pick up where you left off.")
    else:
        print("  run: python -m eval.judges.judge_validation.score_agreement")
    print(rule())
    return 0


if __name__ == "__main__":
    sys.exit(main())
