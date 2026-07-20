# AI 健身热量与计划管理平台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a personal responsive web app that calculates calorie targets, generates 7-day fitness plans, records food/exercise through natural language, updates daily recommendations, and sends DingTalk notifications.

**Architecture:** Use a modular monolith. React + TypeScript serves the responsive UI; FastAPI owns authentication, deterministic calorie calculations, plan/record APIs, AI provider calls, and DingTalk delivery; PostgreSQL stores all user data. Docker Compose runs frontend, backend, a dedicated scheduler, and PostgreSQL on Aliyun.

**Tech Stack:** React, TypeScript, Vite, React Router, TanStack Query, Recharts, CSS; Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic Settings, httpx, APScheduler; PostgreSQL; Docker Compose; pytest, pytest-asyncio, Vitest, React Testing Library, Playwright.

---

## Implementation boundaries

The repository is currently empty except for the approved design specification. The MVP is intentionally split into independently testable slices:

1. Backend foundation and deterministic calorie domain.
2. Profile, goals, body metrics, and daily records.
3. AI plan generation and natural-language recording.
4. Responsive frontend and visual design system.
5. DingTalk notifications, scheduler, deployment, and end-to-end verification.

Do not add multi-user organizations, payments, native mobile apps, photo recognition, wearable sync, or a nutritionist admin panel.

## Repository layout after implementation

```text
backend/
  app/
    api/
    core/
    db/
    models/
    schemas/
    services/
    main.py
  tests/
  alembic/
  pyproject.toml
  Dockerfile
frontend/
  src/
    components/
    features/
    lib/
    pages/
    styles/
    App.tsx
    main.tsx
  tests/
  package.json
  Dockerfile
infra/
  docker-compose.yml
  nginx.conf
  .env.example
scripts/
  dev.ps1
  verify.ps1
docs/
  superpowers/specs/2026-07-20-ai-fitness-calorie-planner-design.md
  superpowers/plans/2026-07-20-ai-fitness-calorie-planner-implementation.md
README.md
.gitignore
```

---

### Task 1: Bootstrap the repository and test runners

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/test_health.py`
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/App.test.tsx`
- Create: `infra/.env.example`
- Modify: `.gitignore`
- Create: `README.md`

- [ ] **Step 1: Write backend dependency and test configuration**

Create `backend/pyproject.toml` with FastAPI, Uvicorn, SQLAlchemy, Alembic, Pydantic Settings, HTTPX, APScheduler, psycopg, pytest, pytest-asyncio, and Ruff. Configure pytest to discover `backend/tests` and use `asyncio_mode = "auto"`.

- [ ] **Step 2: Write the failing health endpoint test**

Create `backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient
from app.main import app


def test_health_endpoint_returns_ok():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 3: Run the backend test and verify the expected failure**

Run from the repository root:

```powershell
python -m pytest backend/tests/test_health.py -q
```

Expected: FAIL because `app.main` and `/health` do not exist.

- [ ] **Step 4: Implement the minimal FastAPI app**

Create `backend/app/main.py`:

```python
from fastapi import FastAPI

app = FastAPI(title="FitPlan AI API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 5: Scaffold the Vite frontend and a visible shell**

Create `frontend/src/App.tsx` with a single `FitPlan AI` heading and create `frontend/src/main.tsx` that mounts it. Add Vitest and React Testing Library configuration.

- [ ] **Step 6: Write the frontend smoke test and run both test runners**

Create `frontend/src/App.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "./App";

describe("App", () => {
  it("renders the product shell", () => {
    render(<App />);
    expect(screen.getByText("FitPlan AI")).toBeInTheDocument();
  });
});
```

Run:

```powershell
python -m pytest backend/tests/test_health.py -q
cd frontend
npm install
npm run test -- --run
npm run build
cd ..
```

Expected: both test suites pass and the frontend build completes.

- [ ] **Step 7: Add repository scripts and commit**

Create `scripts/dev.ps1` to start backend and frontend in separate terminals, and `scripts/verify.ps1` to run backend tests, frontend tests, and the frontend build. Add `.venv/`, `dist/`, `coverage/`, `.env`, and generated caches to `.gitignore`.

```powershell
& python -m pytest backend -q
Push-Location frontend
& npm run test -- --run
& npm run build
Pop-Location
```

Commit:

```powershell
git add backend frontend scripts README.md .gitignore
git commit -m "chore: bootstrap fitplan app"
```

---

### Task 2: Add backend settings, database, migrations, and single-user authentication

**Files:**
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/security.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/db/base.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/api/auth.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_auth.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_initial_user.py`

- [ ] **Step 1: Define environment settings**

Use `pydantic-settings` in `backend/app/core/config.py` with fields `database_url`, `jwt_secret`, `ai_base_url`, `ai_api_key`, `ai_model`, `dingtalk_webhook`, `dingtalk_secret`, and `app_env`. Load `.env` but keep production secrets outside Git.

- [ ] **Step 2: Write authentication tests**

Test that the single account can be initialized once, login returns a bearer token, a protected endpoint accepts the token, and invalid credentials return 401. Use an in-memory SQLite test database only for unit/API tests; production remains PostgreSQL.

- [ ] **Step 3: Implement password hashing and JWT sessions**

Create `security.py` with password hashing and JWT encode/decode functions. Create `User` with `id`, `username`, `password_hash`, and `created_at`. Add `/api/auth/setup`, `/api/auth/login`, and `/api/auth/me`. `/setup` must return 409 after the first account exists.

- [ ] **Step 4: Add SQLAlchemy session dependency and migration**

Create a session factory from `DATABASE_URL`, a declarative base, `get_db`, and Alembic configuration. Generate the initial migration for `users` and verify it applies to a disposable database.

- [ ] **Step 5: Run tests and commit**

Run:

```powershell
python -m pytest backend/tests/test_auth.py -q
```

Expected: all authentication tests pass. Commit:

```powershell
git add backend/app backend/tests backend/alembic.ini backend/alembic
git commit -m "feat: add single-user authentication and database foundation"
```

---

### Task 3: Implement deterministic calorie calculations with TDD

**Files:**
- Create: `backend/app/services/calorie.py`
- Create: `backend/app/schemas/calorie.py`
- Create: `backend/app/api/calorie.py`
- Create: `backend/tests/test_calorie.py`

- [ ] **Step 1: Write failing unit tests for BMR, TDEE, and goals**

Use fixed fixtures to test Mifflin-St Jeor, activity multipliers, and goal adjustments. Include tests for male, female, maintenance, deficit, surplus, and rejection of a target below the configured safety floor.

Example expected contract:

```python
def test_male_mifflin_st_jeor():
    assert calculate_bmr(age=30, sex="male", weight_kg=80, height_cm=180) == 1780


def test_fat_loss_target_is_below_tdee():
    result = calculate_targets(
        age=30, sex="male", weight_kg=80, height_cm=180,
        activity_level="moderate", goal="fat_loss"
    )
    assert result.tdee > result.daily_calories
    assert result.daily_calories >= 1500
```

- [ ] **Step 2: Implement the calculation service**

Expose typed functions:

```python
def calculate_bmr(age: int, sex: str, weight_kg: float, height_cm: float) -> int: ...
def calculate_tdee(bmr: int, activity_level: str) -> int: ...
def calculate_targets(..., goal: str) -> CalorieTargets: ...
```

Use the approved goal values `fat_loss`, `muscle_gain`, and `maintenance`. Return BMR, TDEE, daily calories, protein grams, carb grams, and fat grams. Keep rounding deterministic.

- [ ] **Step 3: Add the preview API**

Implement `POST /api/calorie/preview` so onboarding can show calculated targets before saving. Validate age, height, weight, activity level, sex, and goal with Pydantic.

- [ ] **Step 4: Run tests and commit**

Run:

```powershell
python -m pytest backend/tests/test_calorie.py -q
```

Expected: all calorie tests pass. Commit:

```powershell
git add backend/app/services/calorie.py backend/app/schemas/calorie.py backend/app/api/calorie.py backend/tests/test_calorie.py
git commit -m "feat: add deterministic calorie and macro targets"
```

---

### Task 4: Add profiles, goals, body metrics, food logs, and exercise logs

**Files:**
- Create: `backend/app/models/profile.py`
- Create: `backend/app/models/goal.py`
- Create: `backend/app/models/record.py`
- Create: `backend/app/schemas/profile.py`
- Create: `backend/app/schemas/record.py`
- Create: `backend/app/api/profile.py`
- Create: `backend/app/api/records.py`
- Create: `backend/tests/test_profile_api.py`
- Create: `backend/tests/test_records_api.py`
- Create: `backend/alembic/versions/0002_profile_and_records.py`

- [ ] **Step 1: Write profile and record API tests**

Cover:

- creating and updating the single user's profile;
- saving a goal;
- saving body metrics;
- creating a food log with calories and macros;
- creating an exercise log;
- returning the daily summary with totals and remaining calories;
- rejecting malformed negative quantities.

- [ ] **Step 2: Create SQLAlchemy models and migrations**

Add tables `profiles`, `goals`, `body_metrics`, `food_logs`, and `exercise_logs`. Every row must reference the single authenticated user. Store original text and structured parsed content in `food_logs` so AI corrections remain auditable.

- [ ] **Step 3: Implement profile and record endpoints**

Implement:

```text
GET  /api/profile
PUT  /api/profile
POST /api/body-metrics
GET  /api/body-metrics
POST /api/records/food
POST /api/records/exercise
GET  /api/records/daily?date=YYYY-MM-DD
PATCH /api/records/food/{record_id}
DELETE /api/records/food/{record_id}
POST /api/records/food/{record_id}/undo
```

Use UTC timestamps in storage and convert to the configured user timezone at the API boundary.

- [ ] **Step 4: Implement daily summary calculations**

Add a service that sums active food logs, sums exercise logs, compares totals with the active goal, and returns macro completion percentages. Undo and deleted records must be excluded.

- [ ] **Step 5: Run tests and commit**

Run:

```powershell
python -m pytest backend/tests/test_profile_api.py backend/tests/test_records_api.py -q
```

Expected: all profile and record tests pass. Commit:

```powershell
git add backend/app backend/tests backend/alembic/versions/0002_profile_and_records.py
git commit -m "feat: add profiles body metrics and daily records"
```

---

### Task 5: Add plan versions and 7-day plan generation contracts

**Files:**
- Create: `backend/app/models/plan.py`
- Create: `backend/app/schemas/plan.py`
- Create: `backend/app/services/plan_service.py`
- Create: `backend/app/api/plans.py`
- Create: `backend/tests/test_plan_service.py`
- Create: `backend/tests/test_plan_api.py`
- Create: `backend/alembic/versions/0003_plans.py`

- [ ] **Step 1: Write tests for plan versioning**

Test that a generated plan contains exactly seven dated days, each day has meals and a workout/rest entry, a newer plan becomes active, and previous plans remain readable but inactive.

- [ ] **Step 2: Define typed plan schemas**

Use Pydantic models for `MealPlan`, `WorkoutPlan`, `PlanDay`, `PlanCreate`, and `PlanSummary`. Make all generated JSON serializable and validate that each day has a date, calorie target, meals, and training instruction.

- [ ] **Step 3: Implement persistence and plan APIs**

Create `plans` and `plan_days` tables. Implement:

```text
POST /api/plans
POST /api/plans/generate
GET  /api/plans/current
GET  /api/plans/{plan_id}
POST /api/plans/{plan_id}/activate
```

For this task, use a deterministic fake plan generator in tests and keep the production generator behind an interface that Task 6 will connect to the AI client.

- [ ] **Step 4: Run tests and commit**

Run:

```powershell
python -m pytest backend/tests/test_plan_service.py backend/tests/test_plan_api.py -q
```

Expected: all plan tests pass. Commit:

```powershell
git add backend/app backend/tests backend/alembic/versions/0003_plans.py
git commit -m "feat: add versioned seven-day plans"
```

---

### Task 6: Add the OpenAI-compatible AI client and natural-language records

**Files:**
- Create: `backend/app/services/ai_client.py`
- Create: `backend/app/services/ai_schemas.py`
- Create: `backend/app/services/ai_prompts.py`
- Create: `backend/app/services/ai_record_service.py`
- Create: `backend/app/api/ai.py`
- Create: `backend/app/models/conversation.py`
- Create: `backend/app/schemas/chat.py`
- Create: `backend/app/api/chat.py`
- Create: `backend/tests/fakes.py`
- Create: `backend/tests/test_ai_record_service.py`
- Create: `backend/tests/test_ai_api.py`
- Create: `backend/alembic/versions/0004_conversations.py`

- [ ] **Step 1: Define the AI provider interface and fake client**

Create a protocol:

```python
class AiClient(Protocol):
    async def chat_json(self, *, system: str, user: str) -> dict: ...
    async def chat_text(self, *, system: str, user: str) -> str: ...
```

Create `FakeAiClient` that returns fixture JSON for tests. Production `OpenAICompatibleClient` uses HTTPX, `AI_BASE_URL`, `AI_API_KEY`, and `AI_MODEL`, with a 20-second timeout and a clear provider error.

- [ ] **Step 2: Write failing tests for food parsing and error handling**

Test that a message such as `刚才吃了一个鸡腿堡和一杯奶茶` becomes one food log with two items, estimated macros, original text, and confidence. Test provider timeout, invalid JSON, and missing required fields; each must preserve the original input and return a user-readable error without writing a partial record.

- [ ] **Step 3: Implement structured AI schemas and prompts**

Create `ParsedFoodItem`, `ParsedFoodResult`, `ParsedExerciseResult`, and `PlanGenerationResult`. Prompts must require JSON only, state that quantities are estimates, and instruct the model not to provide medical diagnosis. Keep prompts in `ai_prompts.py`, not inline in route functions.

- [ ] **Step 4: Implement natural-language food and exercise recording**

Implement:

```text
POST /api/records/food/natural-language
POST /api/records/exercise/natural-language
```

The service sends the user text to the AI client, validates the structured result, writes the record, recalculates the daily summary, and returns the adjustment suggestion. Store the conversation and source text.

- [ ] **Step 5: Connect AI plan generation and chat**

Use the same provider interface for 7-day plan generation and `/api/ai/chat`. Pass only a profile summary, current plan, today’s logs, and bounded recent conversation history. Never send secrets or the full database row set to the model.

- [ ] **Step 6: Run tests and commit**

Run:

```powershell
python -m pytest backend/tests/test_ai_record_service.py backend/tests/test_ai_api.py -q
```

Expected: all AI tests pass without a real API key. Commit:

```powershell
git add backend/app backend/tests backend/alembic/versions/0004_conversations.py
git commit -m "feat: add AI natural-language records and chat"
```

---

### Task 7: Build the responsive frontend shell and visual system

**Files:**
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/src/styles/global.css`
- Create: `frontend/src/components/AppShell.tsx`
- Create: `frontend/src/components/BottomNav.tsx`
- Create: `frontend/src/components/SidebarNav.tsx`
- Create: `frontend/src/components/EditorialButton.tsx`
- Create: `frontend/src/components/MetricCard.tsx`
- Create: `frontend/src/components/SectionCard.tsx`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/types.ts`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/components/EditorialButton.test.tsx`

- [ ] **Step 1: Write the button component test**

Test primary and secondary variants, accessible button names, disabled state, and loading label.

- [ ] **Step 2: Add visual tokens**

Define CSS variables for the approved palette: warm off-white background, deep green primary, warm orange accent, muted text, border, card radius, and shadow. Add responsive breakpoints for mobile bottom navigation and desktop sidebar navigation.

- [ ] **Step 3: Implement the Editorial Capsule button**

`EditorialButton` must support `variant="primary" | "accent" | "secondary"`, `loading`, `disabled`, and an optional icon. It must use action copy such as `记录饮食` and `和 AI 调整计划`.

- [ ] **Step 4: Implement the shared shell**

Create an `AppShell` with responsive navigation, a main content area, and a consistent page header. Keep all visual components presentational; data fetching remains in feature pages.

- [ ] **Step 5: Run frontend tests and commit**

Run:

```powershell
cd frontend
npm run test -- --run
npm run build
cd ..
```

Expected: component tests pass and the production build succeeds. Commit:

```powershell
git add frontend/src
git commit -m "feat: add responsive editorial UI system"
```

---

### Task 8: Implement onboarding, dashboard, records, trends, and settings pages

**Files:**
- Create: `frontend/src/pages/OnboardingPage.tsx`
- Create: `frontend/src/pages/DashboardPage.tsx`
- Create: `frontend/src/pages/PlanPage.tsx`
- Create: `frontend/src/pages/RecordsPage.tsx`
- Create: `frontend/src/pages/TrendsPage.tsx`
- Create: `frontend/src/pages/SettingsPage.tsx`
- Create: `frontend/src/features/onboarding/OnboardingForm.tsx`
- Create: `frontend/src/features/dashboard/CalorieSummary.tsx`
- Create: `frontend/src/features/dashboard/TodayPlanCard.tsx`
- Create: `frontend/src/features/dashboard/QuickRecordComposer.tsx`
- Create: `frontend/src/features/dashboard/AiAdjustmentCard.tsx`
- Create: `frontend/src/features/records/RecordList.tsx`
- Create: `frontend/src/features/trends/TrendCharts.tsx`
- Create: `frontend/src/pages/pages.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Write page-level tests with mocked API responses**

Cover:

- onboarding submits profile and displays calculated targets;
- dashboard displays remaining calories and today’s plan;
- natural-language composer submits food text and displays the returned adjustment;
- record list supports undo/delete controls;
- trends page renders a chart container;
- settings page stores AI and DingTalk configuration without displaying secrets.

- [ ] **Step 2: Implement onboarding flow**

Build the multi-step form with client validation for required profile fields. Call `/api/calorie/preview`, display BMR/TDEE/macros, then save the profile and call `/api/plans/generate`.

- [ ] **Step 3: Implement dashboard and quick record composer**

Use TanStack Query for `/api/dashboard`. The composer must submit natural-language text, show a loading state, display parsed calories/macros and the updated remaining calories, and offer undo.

- [ ] **Step 4: Implement plan, records, trends, and settings**

Use Recharts for weight, body-fat, calorie, and exercise-completion trends. Keep chart data transformations in `TrendCharts.tsx`. Implement the approved large-card layout and Editorial Capsule actions.

- [ ] **Step 5: Add route guards and empty/error states**

Route unauthenticated users to setup/login. Show friendly empty states for no records, unavailable AI, and failed notifications. Preserve the original natural-language input when AI parsing fails.

- [ ] **Step 6: Run tests and commit**

Run:

```powershell
cd frontend
npm run test -- --run
npm run build
cd ..
```

Expected: all page tests pass and the build succeeds. Commit:

```powershell
git add frontend/src
git commit -m "feat: add onboarding dashboard records trends and settings"
```

---

### Task 9: Add DingTalk Webhook delivery and scheduled notifications

**Files:**
- Create: `backend/app/services/dingtalk.py`
- Create: `backend/app/services/notification_service.py`
- Create: `backend/app/scheduler/jobs.py`
- Create: `backend/app/scheduler/runner.py`
- Create: `backend/app/models/notification.py`
- Create: `backend/app/schemas/settings.py`
- Create: `backend/app/api/settings.py`
- Create: `backend/tests/test_dingtalk.py`
- Create: `backend/tests/test_notification_service.py`
- Create: `backend/alembic/versions/0005_notifications_and_settings.py`

- [ ] **Step 1: Write DingTalk signing and delivery tests**

Use an HTTPX mock transport to test HMAC signing, successful POST, timeout, non-2xx response, and secret redaction in logs. No test may call a real DingTalk Webhook.

- [ ] **Step 2: Implement the DingTalk client**

Create a client that calculates the timestamp/signature, sends Markdown messages, applies a 10-second timeout, and returns a typed delivery result. Keep Webhook and secret in server-side settings only.

- [ ] **Step 3: Implement notification persistence and strategies**

Add `settings` and `notification_logs`. Implement strategies for `every_record`, `only_over_target`, `hourly_digest`, and `disabled`. Record failures and retry twice with exponential backoff.

- [ ] **Step 4: Implement scheduler jobs**

Create a dedicated scheduler process with two jobs:

- daily plan job at the configured local time;
- post-record feedback job triggered by the notification service.

The daily job must be idempotent for a given user/date so restarting the scheduler does not send duplicate daily messages.

- [ ] **Step 5: Add test notification endpoint**

Implement `POST /api/notifications/test-dingtalk` and `PUT /api/settings`. Return a safe status message without returning the Webhook URL or secret.

- [ ] **Step 6: Run tests and commit**

Run:

```powershell
python -m pytest backend/tests/test_dingtalk.py backend/tests/test_notification_service.py -q
```

Expected: all notification tests pass. Commit:

```powershell
git add backend/app backend/tests backend/alembic/versions/0005_notifications_and_settings.py
git commit -m "feat: add DingTalk notifications and scheduler"
```

---

### Task 10: Add Docker Compose, reverse proxy, database migration flow, and backup scripts

**Files:**
- Create: `infra/docker-compose.yml`
- Create: `infra/nginx.conf`
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `scripts/backup.ps1`
- Create: `scripts/migrate.ps1`
- Modify: `infra/.env.example`
- Modify: `README.md`

- [ ] **Step 1: Write container health checks**

The backend container must expose `/health`, the frontend container must serve the built app, and PostgreSQL must use a health check before backend startup.

- [ ] **Step 2: Implement Dockerfiles**

Use a multi-stage Node build for the frontend and a Python runtime image for the backend. Run the backend as a non-root user. Do not copy `.env` into images.

- [ ] **Step 3: Implement Compose services**

Define `frontend`, `backend`, `scheduler`, and `postgres`. Mount a named PostgreSQL volume. Pass all secrets through an external `.env` file. Expose only the reverse proxy port publicly.

- [ ] **Step 4: Configure reverse proxy and SPA fallback**

Route `/api/` to FastAPI and all other paths to the React app. Add security headers and proxy timeouts suitable for AI calls.

- [ ] **Step 5: Add migration and backup commands**

Create scripts that run Alembic migrations and dump PostgreSQL to a timestamped file. Keep backup output outside the repository and document a restore command.

- [ ] **Step 6: Verify the container stack and commit**

Run:

```powershell
docker compose -f infra/docker-compose.yml config
docker compose -f infra/docker-compose.yml build
docker compose -f infra/docker-compose.yml up -d
docker compose -f infra/docker-compose.yml ps
Invoke-WebRequest http://localhost/health
```

Expected: all services are healthy and `/health` returns `{ "status": "ok" }`. Commit:

```powershell
git add infra backend/Dockerfile frontend/Dockerfile scripts README.md
git commit -m "ops: add Docker deployment and backup flow"
```

---

### Task 11: Add end-to-end verification and production-readiness checks

**Files:**
- Create: `frontend/e2e/mvp-flow.spec.ts`
- Create: `backend/tests/test_mvp_flow.py`
- Modify: `scripts/verify.ps1`
- Modify: `README.md`

- [ ] **Step 1: Write backend integration flow test**

Run against a disposable test database and fake AI client. Verify setup, calorie preview, profile save, plan generation, natural-language food record, daily summary, undo, and notification log creation.

- [ ] **Step 2: Write Playwright smoke flow**

Start the full stack with a test environment and verify:

1. setup screen loads;
2. profile form can be submitted;
3. dashboard shows today’s calorie target;
4. entering food text shows the returned estimate;
5. record list contains the new item;
6. undo removes it from the daily total;
7. mobile viewport shows bottom navigation;
8. desktop viewport shows sidebar navigation.

- [ ] **Step 3: Add failure-path checks**

Verify the UI remains usable when AI returns a timeout and when DingTalk delivery fails. Verify API secrets are not present in frontend build output or response bodies.

- [ ] **Step 4: Run the complete verification script**

Run:

```powershell
./scripts/verify.ps1
```

Expected: backend unit/integration tests pass, frontend tests pass, frontend build passes, Docker Compose configuration is valid, and Playwright smoke tests pass.

- [ ] **Step 5: Commit the verified MVP**

```powershell
git add backend frontend scripts README.md
git commit -m "test: verify end-to-end MVP flow"
```

---

## Final self-review checklist

- [ ] Every approved design section maps to one or more tasks.
- [ ] Calorie calculations remain deterministic and are covered by unit tests.
- [ ] AI parsing is isolated behind an OpenAI-compatible client and fake test implementation.
- [ ] Natural-language records support edit, delete, and undo.
- [ ] Plan versions preserve history.
- [ ] DingTalk delivery is server-side, signed, retried, logged, and idempotent for daily jobs.
- [ ] Responsive mobile and desktop layouts are covered by Playwright smoke tests.
- [ ] Docker deployment uses environment variables and a persistent PostgreSQL volume.
- [ ] No health or medical claims are presented as diagnoses.
- [ ] No placeholders or unspecified implementation choices remain in the plan.


