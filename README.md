# FitPlan AI

FitPlan AI is a minimal full-stack starter for a personal fitness calorie planner.
Business features are intentionally not implemented yet.

## Stack and toolchain

### Backend

Runtime dependencies are declared in `backend/pyproject.toml`:

- FastAPI and Uvicorn for the HTTP API and local ASGI server
- SQLAlchemy and Alembic for the future persistence layer and migrations
- pydantic-settings for future environment-based configuration
- httpx for future outbound API calls
- APScheduler for future scheduled jobs
- psycopg with the binary extra for future PostgreSQL access

Test and developer dependencies are installable with the `test` or `dev` extras:

- pytest
- pytest-asyncio
- Ruff

### Frontend

The frontend is a Vite React TypeScript app with Vitest and React Testing Library.
`frontend/package.json` uses standard npm scripts: `dev`, `test`, `build`, and `preview`.

This workspace currently includes a `frontend/pnpm-lock.yaml` because `npm` was not available in
the execution environment used for task 1. Use `npm install` when npm is installed. If npm is not
available, use the pnpm fallback:

```powershell
cd frontend
pnpm install
pnpm run test -- --run
pnpm run build
```

The helper scripts prefer `npm` when it is available and fall back to `pnpm` otherwise.

## Backend setup

From the repository root, create a virtual environment and install the backend test/dev dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".\backend[test]"
.\.venv\Scripts\python -m pytest backend -q
.\.venv\Scripts\python -m ruff check backend
```

Run the API locally:

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload
```

The health endpoint is available at `GET /health` and returns `{ "status": "ok" }`.

## Frontend setup

With npm:

```powershell
cd frontend
npm install
npm run test -- --run
npm run build
npm run dev
```

With pnpm fallback:

```powershell
cd frontend
pnpm install
pnpm run test -- --run
pnpm run build
pnpm run dev
```

## Development helpers

From the repository root:

```powershell
.\scripts\dev.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1
```

`dev.ps1` and `verify.ps1` prefer `.venv\Scripts\python.exe` from the repository root. If that
file does not exist, they fall back to the system `python` command. They also prefer npm and fall
back to pnpm when npm is unavailable.

Copy `infra/.env.example` to `.env` for local environment configuration when needed.
