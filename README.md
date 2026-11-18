# Agentic Project Simulation Engine

A multi-agent simulator that runs proposed software projects through a gated lifecycle review (design, architecture, build, launch readiness) with role-scoped LLM stakeholders playing the four roles that typically gate-keep real engineering programs: a product manager, an engineering lead, a security/privacy reviewer, and a FinOps/legal reviewer. The simulator's purpose is twofold. As a system, it stress-tests project plans by surfacing the concerns a real cross-functional review would raise. As an evaluation target, it provides a structured environment for measuring how well a stochastic multi-agent system can detect known defects, stay in role, and stay grounded under varying prompt and grounding strategies.

The repository includes the simulator itself, a fixed suite of 10 fintech/payments project scenarios with seeded defects, and a five-layer evaluation harness that produces master tables comparing the baseline (V1) and constrained-decoding (V2) configurations.

## Baseline Results (V1)

10 scenarios, fintech and payments domain, raw-prompting baseline (no retrieval, no tool-use enforcement). Structural, Functional, and Economics rows are produced by `eval/report.py`; Behavioral rows by `eval/metrics/persona.py`. All numbers committed to this README.

| Pillar | Metric | V1 Baseline |
|--------|--------|-------------|
| Structural | Format pass rate | 100% (40/40 agent responses) |
| Structural | Retries used | 2 |
| Behavioral | In-persona rate (LLM judge, 301 concerns) | 0.73 (per agent: 0.55 to 0.91) |
| Behavioral | Judge-to-human agreement (45 hand-labeled turns) | 0.78 raw, 0.67 Cohen's kappa |
| Functional | Defect-detection recall (tagged) | 0.93 |
| Functional | Defect-detection recall (true, after review) | 1.00 |
| Functional | Defect-detection strict precision (floor) | 0.11 |
| Functional | Unmatched-flag decomposition (judge) | 76% legitimate unseeded / 17% partial / 6% drift |
| Economics | Avg cost per scenario (agent runs) | $0.08 |

The two recall numbers report the same underlying behavior at different measurement granularities. Tagged recall is what the scorer produces by matching catalog IDs in concern fields. True recall is what the scorer produces after reviewing the agents' free-text reasoning, which on one scenario identified a seeded defect that the agent recognized but bundled into a related concern instead of tagging separately. The distinction matters because the gap between the two numbers is a tagging-granularity failure, not a detection-capability failure, and the V2 fix for each is different.

Strict precision is reported as a floor, not a truth. It treats every concern that does not match a seeded defect ID as a false positive. The L4 judge decomposes that floor: of the unmatched flags across the suite, 76% were judged as legitimate in-persona catches of gaps not seeded in ground truth, 17% as partially in-role, and 6% as persona drift. True noise is a small minority of what the strict number counts against the system.

## V2 Results: Constrained Decoding

V2 replaces JSON-in-prompt with grammar-constrained structured outputs. The API compiles the Pydantic schema into the decoding grammar, narrowed per call to the calling role, the gate, and the 29-ID defect catalog, so an agent cannot emit a defect ID outside the catalog. Role reviews run concurrently (sectioning) and aggregate through the unchanged deterministic gate rule. Each configuration ran 3 trials of the 10 scenarios. Recall differences are paired by scenario and bootstrapped over the 7 scenarios that seed defects, since trials of one scenario are not independent.

| Metric | V1 (JSON in prompt) | V2 initial | V2 final (all fields required) |
|--------|---------------------|------------|--------------------------------|
| Format pass rate | 120/120 | 119/120 | 120/120 |
| Failed attempts (retries) | 4 | 4 (3 validation, 1 max_tokens) | 0 |
| Tagged recall, mean of 3 trials (SD) | 0.95 (0.04) | 0.81 (0.05) | 0.91 (0.05) |
| Recall change vs V1, paired by scenario [95% CI] | n/a | -0.14 [-0.40, +0.04] | -0.04 [-0.12, +0.05] |
| Seeded defects caught in all 3 trials | 14/16 | 11/16 | 12/16 |
| Strict precision | 0.11 to 0.12 | 0.10 to 0.11 | 0.10 to 0.11 |
| Gate outcome matches expected | 21/30 | 21/30 | 21/30 |
| Wall time per scenario (approx.) | 92 s, sequential | 23 s, parallel | 21 s, parallel |
| Cost per scenario | $0.079 | $0.073 | $0.074 |

**The harness caught a regression.** The initial V2 missed both seeded defects in `scn_007` in all three trials (V1 caught 5 of 6) and raised 26% fewer concerns per run. Structured outputs emit required properties before optional ones. Because `concerns` was optional, the model wrote its decision and summary reasoning before listing concerns, the reverse of V1's order. Making every field required restored concern-first order: `scn_007` recovered in 2 of 3 trials, and suite recall moved to within 0.04 of V1, an interval that includes no change.

**Limits of the comparison.** Seven scenarios with seeded defects is a small sample, so the intervals are wide and only large effects are detectable. V2 final versus V1 is consistent with parity, not proof of it. Enum casing is normalized before scoring, and a wrong-but-valid catalog ID remains possible; strict precision measures that.

**Eval integrity.** Claude Code permission deny rules block the coding agent's edit tools from modifying the answer key (scenarios, defect catalog, human labels, V1 runs), a guard against the test tampering documented in coding agents. A Stop hook runs the offline contract tests and keeps a turn from ending while they fail, and CI runs the same tests with read-only permissions and no secrets. All 90 run files behind this table are in `eval/trials/`, and `python -m eval.compare_trials` recomputes every number in it, including the paired intervals.

## Architecture

The system has two layers: the simulator (which runs scenarios) and the evaluation harness (which measures the simulator). The harness is organized into three communication pillars over five engineering layers.

| Pillar | Layer(s) | What it measures |
|--------|----------|------------------|
| Structural Integrity | L1: Schema validity | Whether agent outputs conform to the Pydantic schema |
| Behavioral Fidelity | L4: Persona fidelity | Whether agents stay in their assigned role |
| Functional Accuracy & Unit Economics | L2: Defect detection | Precision and recall on seeded defects |
| | L3: Retrieval quality | Recall@k, MRR on retrieved playbook chunks |
| | L5: Groundedness | Rate of assertions traceable to project state or retrieved context |
| | Cost | Dollars per full lifecycle simulation |

Phase 1 (V1 baseline) implements L1, L2, and cost. The L4 persona judge shipped ahead of schedule with human-validated calibration. V2 changed how outputs are decoded (see V2 Results); L3 (retrieval) and L5 (groundedness) are not built yet.

## Methodology

A few design decisions matter more than the numbers themselves, and are worth understanding before reading the table closely.

**Closed-enum schemas.** Every choice the model can make at a structural decision point (agent role, gate stage, severity, decision verdict, persona verdict) is a Python enum with `extra="forbid"` enforcement. Without this, hallucinated field values silently pass validation and the L1 metric becomes meaningless. Schema rigor is what makes L1 measure anything at all.

**The defect catalog is vocabulary, not an answer key.** Agents are shown a catalog of 29 canonical defect IDs and asked to tag their concerns with the matching ID when applicable. Any single scenario seeds 0 to 3 defects from that catalog, so the agent receives a vocabulary rather than the list of correct answers. This is what makes L2 scoring deterministic without relying on fuzzy text matching between agent prose and seeded-defect descriptions.

**Strict precision is the floor.** Every concern that does not match a seeded defect ID is counted as a false positive by the strict scorer. In practice these unmatched concerns fall into three categories: real-but-unseeded catches, persona drift (an agent flagging something outside its role), and true noise. The triage workflow distinguishes them by asking three questions of each: does the project state actually support the concern, is the concern in the agent's domain, and is the concern a defect or a wish. The result of triage is a precision number meaningfully higher than the strict floor.

**The judge was calibrated against human labels before its scores were trusted.** The L4 persona judge uses a discrete categorical rubric (in-persona / partial / out-of-persona) and additionally names which role's domain a drifting concern reaches into. Before any judge score entered this README, the judge was run against 45 hand-labeled agent turns sampled across all scenarios and roles: 0.78 raw agreement, 0.67 Cohen's kappa, 0.75 weighted kappa, "substantial" on the Landis & Koch scale. The confusion matrix shows every disagreement is adjacent-category (in-persona vs partial, partial vs out); there are zero opposite-corner disagreements. The judge is reliable on clear cases and negotiates only the same fuzzy boundary a human labeler does. Forty-five labels is a small set, so the kappa carries a wide interval. An uncalibrated judge is an unmeasured instrument.

**Persona drift is asymmetric, and the asymmetry is informative.** In-persona rates by role: security/privacy 0.91, FinOps/legal 0.80, engineering lead 0.63, PM 0.55. The roles with crisp regulatory vocabularies hold persona; the roles whose domains naturally blur into everything bleed. The dominant leaks are PM into engineering territory and the engineering lead into security and FinOps territory. This quantifies which persona prompts need tightening in V2 and in which direction.

**Clean scenarios aren't clean.** Three of the 10 scenarios were designed as "clean" precision negatives. In practice, all three were either blocked or approved-with-conditions because the agents found legitimate gaps. This is honest behavior for a multi-agent review system and the response is to redefine "clean" as "no `blocking`-severity flags" rather than "zero concerns." Real gate reviews work this way.

**One V1 miss was a measurement artifact, not a detection failure.** On the circular-dependency scenario (`scn_007`), the engineering lead identified both seeded defects but combined them into a single concern in its `defect_id` field, leaving the second seeded defect "uncaught" by the tagged-recall scorer. Manual review of the agent's `reasoning` field shows the defect was explicitly identified. A "one defect per concern" constraint would close this gap; V2's structured outputs do not enforce it yet.

## Open Targets

V2 closed the first V1 failure mode below; the rest are open.

- Done in V2: L1 retries fell from 4 across three V1 trials to 0 across three V2 trials (120 agent calls each) with grammar-constrained structured outputs (V2 Results).
- Tagged recall should match true recall (0.93 vs 1.00 in V1) once concerns are constrained to one defect each.
- Strict precision (0.10 to 0.11 in both V1 and V2) should improve with two interventions: a retrieval layer that grounds agents in gate-specific playbooks (so they raise concerns from documented review patterns rather than from generic best-practice prior), and persona-prompt tightening now targeted by the measured drift asymmetry (PM at 0.55 and engineering lead at 0.63 in-persona are the weak prompts; their dominant leak directions are documented above).
- A separate cross-cutting "release coordinator" agent will be evaluated for systemic concerns (dependency cycles, sequencing, multi-service coordination) that the four role-scoped agents reliably miss on raw prompting.

## Repository Layout

```
.
├── core_engine/
│   └── schemas.py              # Pydantic models shared by the simulator and harness
├── eval/
│   ├── defect_catalog.yaml     # 29 canonical defect IDs
│   ├── scenarios/              # 10 YAML test fixtures
│   ├── runners/
│   │   └── run_scenario.py     # Executes one scenario through the agent system
│   ├── metrics/
│   │   ├── schema.py           # L1 scorer
│   │   ├── defects.py          # L2 scorer
│   │   └── persona.py          # L4 aggregator: in-persona rate, encroachment, flag partition
│   ├── judges/
│   │   ├── persona_judge.py    # L4 discrete-rubric judge
│   │   └── judge_validation/   # 45 human-labeled turns + agreement scorer
│   ├── runs/                   # V1 baseline ScenarioRun JSONs (read-only)
│   ├── trials/                 # 3-trial runs behind the V2 Results table
│   ├── runs_persona/           # Per-scenario judge verdicts
│   ├── report.py               # Aggregates L1 + L2 into the master table
│   ├── compare_trials.py       # Recomputes the V2 Results table from eval/trials/
│   └── report.md               # Latest generated report
├── tests/                      # Offline contract tests (no API calls), run in CI
├── .github/workflows/ci.yml    # Runs the tests on push and pull request
├── .claude/settings.json       # Claude Code permission rules and Stop-hook test gate
├── CLAUDE.md                   # Commands and rules for Claude Code sessions
└── docs/
    └── evaluation-harness-spec.md   # Internal spec for the eval harness
```

## Running It

Setup:

```bash
pip install anthropic pydantic pyyaml python-dotenv pytest
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

Run the offline tests (no API key needed):

```bash
python -m pytest -q
```

Run one scenario (writes to `eval/runs_v2/`; `eval/runs/` holds the V1 baseline):

```bash
python -m eval.runners.run_scenario eval/scenarios/scn_001_pii_logging.yaml
```

Run the full suite:

```bash
for f in eval/scenarios/scn_*.yaml; do
    python -m eval.runners.run_scenario "$f"
done
```

Score and generate the report (`--runs-dir eval/runs` scores the V1 baseline):

```bash
python -m eval.report --runs-dir eval/runs_v2 --out eval/report_v2.md
```

Judge persona fidelity and validate the judge (L4):

```bash
python -m eval.metrics.persona
python -m eval.judges.judge_validation.score_agreement
```

The V1 table at the top of this README is produced by those commands. Each scenario costs approximately $0.08 on Claude Sonnet at the time of this baseline; the full suite is around $0.80. Judging all 301 concerns with an Opus-class judge cost approximately $5, so re-judging is cached per scenario and only re-runs with `--force`.
