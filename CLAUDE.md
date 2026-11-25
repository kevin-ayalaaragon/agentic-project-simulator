# ProgramDynamics

## Commands
- Install: `pip install anthropic pydantic pyyaml python-dotenv pytest`
- Tests (no API calls): `python -m pytest -q`; one file: `python -m pytest tests/test_runner_contract.py -q`
- One scenario (paid API call, needs `ANTHROPIC_API_KEY` in `.env`): `python -m eval.runners.run_scenario eval/scenarios/<file>.yaml --mode v2|control|agent|rag --output-dir eval/runs_v2` (`rag` also needs `PD_PG_DSN` and `requirements-rag.txt`; only the security reviewer retrieves, other roles run as control)
- Report: `python -m eval.report --runs-dir eval/runs_v2`; V2/V3 comparison: `python -m eval.compare_trials --baseline v2 --configs v2 v3_control v3_agent`
- Retrieval (L3) deps: `pip install -r requirements-rag.txt`. Store tests need Postgres + pgvector: `PD_PG_DSN=postgresql://... python -m pytest -m pg` (skipped by default via pytest.ini)
- Rebuild retrieval artifacts (downloads; commit the outputs): `python -m rag.corpus.build`, `python -m rag.embed`, `python -m eval.retrieval.run_l3 --embed-queries`; baseline: `python -m eval.retrieval.run_l3` (needs `PD_PG_DSN`)

## Rules
- Agent output shape is defined only by the Pydantic models in `core_engine/schemas.py`; the API enforces it through `output_config`, so prompts carry no format instructions.
- The eval answer key (`eval/scenarios/`, `eval/defect_catalog.yaml`, `eval/judges/judge_validation/` labels), the scenario inputs in `eval/artifacts.yaml`, and recorded runs in `eval/runs/` and `eval/trials/` are read-only; permission rules in `.claude/settings.json` block edits.
- Ask before running anything that calls the API; each scenario run costs money.
