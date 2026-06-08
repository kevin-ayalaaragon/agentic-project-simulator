# Phase 1 Build Notes

Session log for the Agentic Project Simulation Engine. Running record of what was built, what was fixed, and what is still open.

## Files created

**`core_engine/schemas.py`**
Pydantic models for the agent system and eval harness. Closed-enum types for agent roles, gates, decisions, severity, and outcomes. `AgentResponse` is the contract every agent call must conform to. `RaisedConcern` carries the `defect_id` field that makes L2 scoring deterministic. `ScenarioRun` is the unit of output the scorers will read. `extra="forbid"` is set everywhere so hallucinated fields fail validation.

**`eval/scenarios/`**
10 YAML fixtures for Phase 1. Seven defective (2 security/privacy, 2 scope creep, 2 architecture, 1 FinOps) and three clean. Fintech/payments domain.

**`eval/defect_catalog.yaml`**
28 canonical defect IDs across all four categories. Larger than any single scenario uses so the agent gets vocabulary, not the answer key.

**`eval/runners/run_scenario.py`**
Loads a YAML scenario, calls all four agents sequentially, parses each response through Pydantic with one retry on failure, aggregates outcomes (block beats approve_with_conditions beats approve), writes a ScenarioRun JSON to `eval/runs/`. Baseline is intentionally weak: raw JSON-in-prompt, no tool use, no retrieval. The weakness is the point; V2 optimizations need somewhere to go.

## Fixes applied after the scn_008 smoke test

1. Bumped `MAX_TOKENS` from 1024 to 4096. The security_privacy_agent was getting truncated mid-JSON and silently dropped from results.
2. Added a `WARN:` print to stderr when an agent produces no valid response after retry. No more silent agent dropouts.
3. Added `encoding="utf-8"` to the JSON write call so non-ASCII characters render correctly on Windows.

## Open issue, deferred

The clean scenarios (008, 009, 010) are not actually clean enough to serve as L2 precision negatives. The agents found legitimate gaps in them and flagged them. Two paths:

- Harden the clean fixtures with more artifacts (rollback_plan, pci_scope_review, and so on).
- Redefine "clean" as "no `blocking` severity flags" rather than "zero concerns."

Path B is more honest to how real gate reviews work. Decision deferred until scn_001 (defective scenario) has been run.

## Locked decisions

- Domain: fintech and payments. Matches the BAH transaction-platform experience and gives interview authenticity.
- Eval harness spec doc is final; that markdown file is the master reference.
- Model: claude-sonnet-4-6.
- Pricing constants: $3 per million input tokens, $15 per million output tokens. Verify against anthropic.com/pricing before quoting any cost numbers externally.
- Spend safety: $5 monthly limit on the API account, $5 in credits.

## Cost calibration from scn_008

About $0.10 per scenario at current verbosity. Full 10-scenario baseline projects to about $1.00. Well within the $5 budget. This is the V1 cost number that V2 optimization needs to improve on, so the high baseline is desirable for the project narrative.

## Status in the build order

Phase 1, partway through.

Done:
- Schemas
- 10 scenarios
- Runner, smoke-tested

Still to do in Phase 1:
- Apply the three runner fixes above
- Re-run scn_008 to verify all four agents respond
- Run scn_001 to see how the security agent handles seeded defects
- Build the L1 and L2 scorers
- Establish the true baseline numbers
