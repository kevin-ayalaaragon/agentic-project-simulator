# Agentic Project Simulation Engine

A multi-agent simulator that runs proposed software projects through a gated lifecycle review (design, architecture, build, launch readiness) with autonomous LLM stakeholders playing the four roles that typically gate-keep real engineering programs: a product manager, an engineering lead, a security/privacy reviewer, and a FinOps/legal reviewer. The simulator's purpose is twofold. As a system, it stress-tests project plans by surfacing the concerns a real cross-functional review would raise. As an evaluation target, it provides a structured environment for measuring how well a stochastic multi-agent system can detect known defects, stay in role, and stay grounded under varying prompt and grounding strategies.

The repository includes the simulator itself, a fixed suite of 10 fintech/payments project scenarios with seeded defects, and a five-layer evaluation harness that produces a master table comparing baseline (V1) and grounded (V2) configurations.

## V1 Baseline Results

10 scenarios, fintech and payments domain, raw-prompting baseline (no retrieval, no tool-use enforcement, no judge layer). Numbers are produced directly by `eval/report.py` and committed to this README.

| Pillar | Metric | V1 Baseline |
|--------|--------|-------------|
| Structural | Format pass rate | 100% (40/40 agent responses) |
| Structural | Retries used | 2 |
| Functional | Defect-detection recall (tagged) | 0.93 |
| Functional | Defect-detection recall (true, after review) | 1.00 |
| Functional | Defect-detection strict precision (floor) | 0.11 |
| Economics | Avg cost per scenario | $0.08 |

The two recall numbers report the same underlying behavior at different measurement granularities. Tagged recall is what the scorer produces by matching catalog IDs in concern fields. True recall is what the scorer produces after reviewing the agents' free-text reasoning, which on one scenario identified a seeded defect that the agent recognized but bundled into a related concern instead of tagging separately. The distinction matters because the gap between the two numbers is a tagging-granularity failure, not a detection-capability failure, and the V2 fix for each is different.

Strict precision is reported as a floor, not a truth. It treats every concern that does not match a seeded defect ID as a false positive. In practice, most unmatched concerns are either legitimate issues not seeded in ground truth or persona drift, neither of which is true noise. The triage workflow described under [Methodology](#methodology) separates these.

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

Phase 1 (V1 baseline) implements L1, L2, and cost. Phases 2 and 3 add the remaining layers along with the corresponding system improvements that those layers measure.

## Methodology

A few design decisions matter more than the numbers themselves, and are worth understanding before reading the table closely.

**Closed-enum schemas.** Every choice the model can make at a structural decision point (agent role, gate stage, severity, decision verdict, persona verdict) is a Python enum with `extra="forbid"` enforcement. Without this, hallucinated field values silently pass validation and the L1 metric becomes meaningless. Schema rigor is what makes L1 measure anything at all.

**The defect catalog is vocabulary, not an answer key.** Agents are shown a catalog of 28 canonical defect IDs and asked to tag their concerns with the matching ID when applicable. Any single scenario seeds 0 to 3 defects from that catalog, so the agent receives a vocabulary rather than the list of correct answers. This is what makes L2 scoring deterministic without relying on fuzzy text matching between agent prose and seeded-defect descriptions.

**Strict precision is the floor.** Every concern that does not match a seeded defect ID is counted as a false positive by the strict scorer. In practice these unmatched concerns fall into three categories: real-but-unseeded catches, persona drift (an agent flagging something outside its role), and true noise. The triage workflow distinguishes them by asking three questions of each: does the project state actually support the concern, is the concern in the agent's domain, and is the concern a defect or a wish. The result of triage is a precision number meaningfully higher than the strict floor.

**Clean scenarios aren't clean.** Three of the 10 scenarios were designed as "clean" precision negatives. In practice, all three were either blocked or approved-with-conditions because the agents found legitimate gaps. This is honest behavior for a multi-agent review system and the response is to redefine "clean" as "no `blocking`-severity flags" rather than "zero concerns." Real gate reviews work this way.

**One V1 miss was a measurement artifact, not a detection failure.** On the circular-dependency scenario (`scn_007`), the engineering lead identified both seeded defects but combined them into a single concern in its `defect_id` field, leaving the second seeded defect "uncaught" by the tagged-recall scorer. Manual review of the agent's `reasoning` field shows the defect was explicitly identified. The V2 fix is a "one defect per concern" constraint enforced through tool use.

## What V2 Targets

The V1 baseline establishes specific failure modes that V2 is designed to address.

- L1 retries (currently 2 across the suite) should drop to 0 with tool-use enforcement of the response schema.
- Tagged recall should match true recall (currently 0.93 vs 1.00) once concerns are constrained to one defect each.
- Strict precision should improve significantly with two interventions: a retrieval layer that grounds agents in gate-specific playbooks (so they raise concerns from documented review patterns rather than from generic best-practice prior), and persona-prompt tightening that reduces cross-domain encroachment.
- A separate cross-cutting "release coordinator" agent will be evaluated for systemic concerns (dependency cycles, sequencing, multi-service coordination) that the four role-scoped agents reliably miss on raw prompting.

## Repository Layout

```
.
├── core_engine/
│   └── schemas.py              # Pydantic models shared by the simulator and harness
├── eval/
│   ├── defect_catalog.yaml     # 28 canonical defect IDs
│   ├── scenarios/              # 10 YAML test fixtures
│   ├── runners/
│   │   └── run_scenario.py     # Executes one scenario through the agent system
│   ├── metrics/
│   │   ├── schema.py           # L1 scorer
│   │   └── defects.py          # L2 scorer
│   ├── runs/                   # ScenarioRun JSONs (one per execution)
│   ├── report.py               # Aggregates L1 + L2 into the master table
│   └── report.md               # Latest generated report
└── docs/
    ├── evaluation-harness-spec.md   # Internal spec for the eval harness
    └── PHASE1_BUILD_NOTES.md        # Build log
```

## Running It

Setup:

```bash
pip install anthropic pydantic pyyaml python-dotenv
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

Run one scenario:

```bash
python -m eval.runners.run_scenario eval/scenarios/scn_001_pii_logging.yaml
```

Run the full suite:

```bash
for f in eval/scenarios/scn_*.yaml; do
    python -m eval.runners.run_scenario "$f"
done
```

Score and generate the report:

```bash
python -m eval.report
```

The master table at the top of this README is produced by that last command. Each scenario costs approximately $0.08 on Claude Sonnet at the time of this baseline; the full suite is around $0.80.
