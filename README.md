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

## Docker 与阿里云 ECS 部署

仓库提供了 PostgreSQL、后端、前端 Nginx 反向代理的一键容器编排：

- backend/Dockerfile：启动前自动执行 Alembic 数据库迁移。
- frontend/Dockerfile：构建 React 静态站点并由 Nginx 提供服务。
- infra/docker-compose.yml：应用、数据库和持久化卷。
- infra/nginx.conf：前端路由回退，并将 /api/ 与 /health 代理到后端。

### 1. 准备 ECS

建议使用 Ubuntu 22.04/24.04 的阿里云 ECS，安装 Docker Engine 与 Docker Compose Plugin；在安全组中至少放通 TCP 80，如配置域名和 HTTPS 再放通 TCP 443。不要将 PostgreSQL 的 5432 端口直接暴露到公网。

    sudo apt update
    sudo apt install -y ca-certificates curl git
    # 按 Docker 官方文档安装 Docker Engine 与 docker-compose-plugin
    sudo usermod -aG docker $USER

重新登录后拉取项目并创建生产环境变量文件：

    git clone <your-repository-url> fitplan-ai
    cd fitplan-ai
    cp infra/.env.example infra/.env
    chmod 600 infra/.env

编辑 infra/.env，至少填写：

    JWT_SECRET=<使用 openssl rand -hex 32 生成的随机值>
    POSTGRES_PASSWORD=<高强度数据库密码>
    AI_BASE_URL=<你的 OpenAI 兼容中转站地址>
    AI_API_KEY=<中转站 API Key>
    AI_MODEL=<模型名称>

AI 相关值可以暂时留空，但 AI 对话、计划生成及自然语言解析会返回“尚未配置”的提示。密码若包含 URL 特殊字符，建议使用仅含字母、数字、下划线和短横线的强密码，避免 PostgreSQL 连接 URL 解析问题。

### 2. 启动与检查

    cd infra
    docker compose up -d --build
    docker compose ps
    curl http://127.0.0.1/health

浏览器访问 http://<ECS 公网 IP>/ 即可使用。查看日志：

    docker compose logs -f backend
    docker compose logs -f web

升级版本时，在项目根目录拉取代码后重新构建：

    git pull
    cd infra
    docker compose up -d --build

数据库数据保存在 Docker volume postgres_data 中；不要在有数据的生产环境执行 docker compose down -v。

### 3. 配置钉钉每日计划提醒（可选）

1. 在钉钉群里添加“自定义机器人”，复制 Webhook 到 DINGTALK_WEBHOOK。
2. 如果机器人安全设置启用了“加签”，将钉钉生成的密钥写入 DINGTALK_SECRET；未启用加签时留空即可。
3. 设置 DINGTALK_DAILY_PUSH_HOUR 和 DINGTALK_DAILY_PUSH_MINUTE，默认每天 08:00（Asia/Shanghai）。
4. 重启后端：docker compose up -d --force-recreate backend。

推送内容包含当日热量目标、当前可用热量、当天饮食安排和训练提示。若未配置 Webhook，调度器不会启动，也不会影响应用正常运行。

### 4. 域名与 HTTPS（建议）

生产环境建议通过阿里云 DNS 将域名 A 记录指向 ECS 公网 IP，并在 Nginx 或阿里云负载均衡上配置 HTTPS 证书。当前容器内置 Nginx 仅监听 80 端口；可以在 ECS 前置 Caddy、Nginx 或负载均衡来终止 TLS，再转发到本应用的 80 端口。
