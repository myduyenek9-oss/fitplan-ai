# FitPlan AI

FitPlan AI is a minimal full-stack starter for a personal fitness calorie planner.
Business features are intentionally not implemented yet.

## Stack

- Backend: FastAPI, pytest, pytest-asyncio
- Frontend: Vite, React, TypeScript, Vitest, React Testing Library

## Backend

From the repository root, create a virtual environment and install the test dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".\backend[test]"
python -m pytest backend -q
```

Run the API locally:

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload
```

The health endpoint is available at `GET /health` and returns `{ "status": "ok" }`.

## Frontend

```powershell
cd frontend
npm install
npm run test -- --run
npm run build
npm run dev
```

## Development helpers

From the repository root:

```powershell
.\scripts\dev.ps1
.\scripts\verify.ps1
```

Copy `infra/.env.example` to `.env` for local environment configuration when needed.
