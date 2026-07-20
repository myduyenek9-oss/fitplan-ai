# Task 1 TDD Log

This log records commands and outcomes observed while bootstrapping task 1 and while addressing
the follow-up specification review. It intentionally records only observed facts.

## Initial bootstrap red/green observations

- Red: `python -m pytest backend/tests/test_health.py -q`
  - Result: failed during collection with `ModuleNotFoundError: No module named 'app'` before the
    FastAPI app was implemented.
- Red: `pnpm test -- --run` from `frontend`
  - Result: failed because `frontend/package.json` did not exist yet.
- Green: `python -m pytest backend -q`
  - Result: `1 passed` after adding the minimal FastAPI app and `/health` route.
- Green: `pnpm run test -- --run` from `frontend`
  - Result: `1 test passed` after adding the Vite React shell and smoke test.
- Green: `pnpm run build` from `frontend`
  - Result: Vite production build completed.
- Green: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1` with the
  Codex-provided Node runtime added to `PATH`
  - Result: backend pytest, frontend Vitest, and frontend build completed.

## Follow-up review red observations

- Red: `python -m pytest backend/tests/test_project_config.py -q`
  - Result: `4 failed`.
  - Observed failures covered missing SQLAlchemy/Alembic/pydantic-settings/httpx/APScheduler/psycopg
    runtime dependencies, missing Ruff test/dev dependency, scripts not preferring
    `.venv\Scripts\python.exe`, verify not running Ruff, and README not documenting the complete
    toolchain and npm/pnpm fallback.

## Follow-up review green observations

- Green: `python -m pytest backend/tests/test_project_config.py -q`
  - Result: `4 passed` after updating backend dependencies, scripts, and README.
- Green: `python -m pip install -e ".\backend[test]"`
  - Result: editable backend install succeeded and installed the newly declared dependencies,
    including SQLAlchemy, Alembic, psycopg-binary, and Ruff.
- Green: `python -m pytest backend -q`
  - Result: `5 passed`.
- Green: `python -m ruff check backend`
  - Result: `All checks passed!`.
- Green: `pnpm run test -- --run` from `frontend` with the Codex Node runtime on `PATH`
  - Result: `1 test passed`.
- Green: `pnpm run build` from `frontend` with the Codex Node runtime on `PATH`
  - Result: Vite production build completed.
- Green: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1`
  - Result: backend pytest reported `5 passed`, Ruff reported `All checks passed!`, frontend Vitest
    reported `1 test passed`, and the Vite production build completed.
