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
`frontend/package.json` uses standard scripts: `dev`, `test`, `build`, and `preview`. The package
manager is explicitly pinned as `pnpm@11.9.0`, and the committed `frontend/pnpm-lock.yaml` is the
authoritative lock file. Do not generate or commit an npm `package-lock.json`; npm is only a fallback
when pnpm is unavailable.

Vite 7 requires Node.js `^20.19.0 || >=22.12.0`, declared in `frontend/package.json`. The helper
scripts check the active Node version and, when available, prepend the Codex bundled Node runtime
(`%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin`)
before failing with a clear error.

This workspace includes `frontend/pnpm-lock.yaml` because npm was not available in the execution
environment used for task 1. The normal install path is pnpm:

```powershell
cd frontend
pnpm install
pnpm run test -- --run
pnpm run build
```

If pnpm is unavailable, the same scripts can run with npm as a fallback:

```powershell
cd frontend
npm install
npm run test -- --run
npm run build
```

Do not commit an npm `package-lock.json`; the committed pnpm lock remains authoritative. The helper
scripts prefer pnpm and fall back to npm only when pnpm is unavailable.

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

With pnpm (preferred):

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
file does not exist, they fall back to the system `python` command. They also prefer pnpm and fall
back to npm when pnpm is unavailable. Before frontend commands, they validate the Vite-compatible
Node.js version and try the bundled Codex Node runtime when available.

Copy `infra/.env.example` to `.env` for local environment configuration when needed.
