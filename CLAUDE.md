# ProgramDynamics

## Commands
- Install: `pip install anthropic pydantic pyyaml python-dotenv pytest`
- Tests (no API calls): `python -m pytest -q`; one file: `python -m pytest tests/test_runner_contract.py -q`
- One scenario (paid API call, needs `ANTHROPIC_API_KEY` in `.env`): `python -m eval.runners.run_scenario eval/scenarios/<file>.yaml --output-dir eval/runs_v2`
- Report: `python -m eval.report --runs-dir eval/runs_v2`

## Rules
- Agent output shape is defined only by the Pydantic models in `core_engine/schemas.py`; the API enforces it through `output_config`, so prompts carry no format instructions.
- The eval answer key (`eval/scenarios/`, `eval/defect_catalog.yaml`, `eval/judges/judge_validation/` labels) and the V1 baseline in `eval/runs/` are read-only; permission rules in `.claude/settings.json` block edits.
- Ask before running anything that calls the API; each scenario run costs money.
