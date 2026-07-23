# FitPlan AI

FitPlan AI 是一个全栈个人健身与热量规划应用：支持账号和目标设置、每日饮食/运动记录、7 天计划、AI 教练聊天、自然语言补记，以及可选的钉钉每日提醒。

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

Authentication uses a single initialized user account. Before using `/api/auth/login`, set a strong
`JWT_SECRET`; generate one with `openssl rand -hex 32` and keep it out of source control. The example
value in `infra/.env.example` is a placeholder and is rejected by authentication operations. The default
`DATABASE_URL` targets PostgreSQL; tests override it with in-memory SQLite.

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


## 产品功能

- 根据资料、活动水平和减脂/维持/增肌目标计算每日热量与三大营养素。
- 生成并保存 7 天饮食与训练计划；可在 AI 教练中持续交流并调整计划。
- 用自然语言补记饮食或运动，例如“下午多吃了一块蛋糕”“慢跑了 35 分钟”；系统会更新当日剩余热量，饮食误记可撤销。
- 可配置 OpenAI 兼容的中转 API（AI_BASE_URL、AI_API_KEY、AI_MODEL）。
- 可选的钉钉群机器人每日计划推送，按中国标准时间（Asia/Shanghai）运行。

## Docker 与阿里云 ECS / 1Panel 部署

仓库提供 PostgreSQL、FastAPI 后端、React 前端 Nginx 的 Docker Compose 编排：

- `backend/Dockerfile`：启动前自动执行 Alembic 数据库迁移。
- `frontend/Dockerfile`：构建 React 静态站点并由 Nginx 提供服务。
- `infra/docker-compose.yml`：应用、数据库和持久化卷。
- `infra/nginx.conf`：前端路由回退，并将 `/api/` 与 `/health` 代理到后端。

为了避免与服务器上已有网站争抢 80/443，生产 Compose 默认只监听服务器本机的 `127.0.0.1:18081`，再由 1Panel/OpenResty 反向代理。PostgreSQL 和后端 API 不直接暴露到公网。

完整的 1Panel 图形化部署、域名/独立端口配置、生产环境变量、Git 自动部署、备份与回滚步骤见：

- [`docs/1panel-deploy.md`](docs/1panel-deploy.md)

生产环境不要提交 `infra/.env`，也不要对有数据的环境执行 `docker compose down -v`。