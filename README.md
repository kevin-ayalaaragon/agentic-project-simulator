# Evaluation Harness Spec: Agentic Project Simulation Engine

## Purpose

This harness measures whether the simulator behaves correctly under stress and produces the
before/after table reported in the README. The goal is verifiable telemetry, not coverage for
its own sake.

## Status

Phase 1 is implemented: L1 (schema validity), L2 (defect detection), and cost instrumentation,
across 10 scenarios. L3, L4, and L5 are specified below but not yet built. The README reports
Phase 1 results only.

## Architecture: Three Pillars, Five Layers

Build with five layers. Report with three pillars.

| Pillar | Layer(s) | What it measures |
|---|---|---|
| Structural Integrity | L1: Schema validity | Outputs conform to Pydantic schema |
| Behavioral Fidelity | L4: Persona fidelity | Agents stay in role (LLM-as-judge) |
| Functional Accuracy & Unit Economics | L2: Defect detection | Precision/recall on seeded defects |
| | L3: Retrieval quality | Recall@5, MRR on RAG |
| | L5: Groundedness | Unsupported assertion rate |
| | Cost | $/run, tokens, latency |

## The Layers

### L1: Schema validity (deterministic)
Validate every agent output against Pydantic models with retry. Metric: format pass rate.
Target 100%.

### L2: Defect detection (the core)
Each YAML scenario carries ground-truth seeded defects. Run the simulator, collect raised
flags, map to defect IDs.
- Recall = caught defects / total seeded defects
- Precision = real flags / total flags

Nuance: an unmatched flag is not automatically a false positive. The agent may have caught an
unseeded gap. Unmatched flags are reviewed by hand and ground truth is updated as the catalog
matures. Automated metrics need human grounding to stay meaningful.

### L3: Retrieval quality
Maintain 20 labeled `(query, relevant_chunk_ids)` pairs. Metrics: Recall@5 and Mean Reciprocal
Rank.

### L4: Persona fidelity (LLM-as-judge)
Use a separate model or call as judge. Discrete categorical rubric, never a 1 to 5 scale
(numeric scales drift between runs):
- `IN_PERSONA` / `PARTIAL` / `OUT_OF_PERSONA`

Validate the judge. Hand-label 20 turns, run the judge on them, report judge-to-human
agreement. An unvalidated judge is an unmeasured instrument.

### L5: Groundedness
Every factual assertion must trace to (a) the project state YAML or (b) a retrieved playbook
chunk. Otherwise it is unsupported. Run with constraint enforcement off and then on. The delta
is the hallucination-reduction number.

### Financial instrumentation
Wrap all API calls in middleware that logs prompt and completion tokens per turn, latency per
call, and dollar cost per full lifecycle simulation. Cost is a headline metric, not a footnote.

## Dataset: 25 YAML Scenarios (10 implemented)

Domain: fintech and payments. The domain has well-defined compliance and architectural failure
modes, which makes ground-truth defect seeding tractable and keeps scenarios realistic rather
than synthetic.

Composition:
- 5 clean (precision negatives)
- 5 security and privacy gaps
- 5 scope creep / missing acceptance criteria
- 5 architecture flaws / dependency deadlocks
- 5 resource and FinOps issues

Example fixture:

```yaml
id: scn_024_unregulated_vendor_integration
description: >
  Payment microservice integrates a third-party vendor with no data
  retention policy and no SLA.
project_state:
  name: "Global Pay Core"
  stage: "architecture_review_gate"
  artifacts: ["system_architecture_v1.2"]
seeded_defects:
  - id: def_missing_data_retention
    should_be_caught_by: "security_privacy_agent"
    at_gate: "architecture_review_gate"
  - id: def_missing_sla
    should_be_caught_by: "finops_legal_agent"
    at_gate: "architecture_review_gate"
expected_gate_outcome: "blocked"
```

## Repo Architecture

```
eval/
  scenarios/              # 25 YAML fixtures
  retrieval_labels/       # query -> chunk_id pairs
  runners/
    run_scenario.py       # executes the agent system against one scenario
  metrics/
    schema.py             # L1
    defects.py            # L2 precision/recall
    retrieval.py          # L3 recall@k, MRR
    grounding.py          # L5 unsupported assertion rate
  judges/
    persona_judge.py      # L4 discrete rubric
    judge_validation/     # human-labeled calibration set
  report.py               # writes the master table into README.md
  run_all.py              # CLI entrypoint
```

## Handling Stochasticity

Set temperature to 0 where the design allows. Where variability is intended (stakeholder agents
should not be fully deterministic), run each scenario 3 to 5 times and report mean plus spread.
A metric reported without its variance is incomplete.

## The Master Table

`report.py` writes this directly into the repo README. Cells stay blank until the code
populates them. Illustrative numbers are never pre-filled. Every figure traces to a committed
run, and any number that cannot be reproduced from run data does not belong in the table.

| Pillar | Metric | Baseline (V1: raw prompts) | Optimized (V2: schema + RAG) |
|---|---|---|---|
| Structural | Format pass rate | [run data] | [run data] |
| Behavioral | In-persona rate | [run data] | [run data] |
| Behavioral | Judge-to-human agreement | [run data] | n/a |
| Functional | Defect recall / precision | [run data] | [run data] |
| Functional | Retrieval recall@5 | [run data] | [run data] |
| Functional | Unsupported assertion rate | [run data] | [run data] |
| Economics | Cost per lifecycle run | [run data] | [run data] |

Report only numbers the harness produced. A metric whose computation cannot be described from
the code is not a measurement.

## Build Order

**Phase 1.** Define Pydantic schemas. Write 10 YAML scenarios (7 with defects, 3 clean). Code
L1 and L2 scorers. Run to capture the true baseline.

**Phase 2.** Add ChromaDB with playbook docs. Build L3 scoring. Scale the dataset to 25.

**Phase 3.** Implement the discrete persona judge and judge validation set. Build the grounding
parser. Run the optimization loop and populate the optimized column.

Ship Phase 1 before touching Phase 3. A finished two-layer harness beats an abandoned
five-layer one.
