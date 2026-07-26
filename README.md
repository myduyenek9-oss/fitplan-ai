# FitPlan AI

> 吃得明白，练得刚好。

FitPlan AI 是一个面向个人健身场景的全栈健康管理应用。用户可以维护个人身体资料和健身目标，计算每日热量与三大营养素，生成并保存 7 天饮食/训练计划，通过自然语言记录饮食和运动，并与 AI 教练持续对话，让计划根据真实执行情况进行调整。

项目采用前后端分离架构，后端提供鉴权、计算、记录、计划、AI 对话和钉钉通知 API；前端提供响应式 Web/PWA 界面；生产环境使用 Docker Compose 部署 PostgreSQL、FastAPI 和 Nginx，并通过 1Panel/OpenResty 反向代理对外提供访问。

## 项目亮点

- **个性化热量计算**：基于性别、年龄、身高、体重、活动水平和目标，计算每日热量目标及蛋白质、碳水、脂肪建议。
- **可持续的 7 天计划**：生成具体到餐食、食材、份量和训练动作的周计划，支持保存、激活、重新生成和延迟训练日。
- **自然语言记录**：支持输入“刚刚吃了两个烧烤，慢跑了十分钟”，自动识别饮食和运动，分别保存热量并同步首页汇总。
- **AI 教练上下文**：AI 请求只读取当前登录用户的资料、目标、计划、当天记录和近期聊天，避免不同用户之间的数据污染。
- **局部计划调整**：在不破坏周计划整体结构的前提下，支持替换指定日期的一顿餐食、调整训练和延迟计划。
- **完整记录管理**：支持饮食/运动记录编辑、删除和撤销，按真实时间排序并汇总每日营养和活动消耗。
- **钉钉每日推送**：支持用户自己的钉钉群机器人配置，敏感配置加密保存，按 Asia/Shanghai 时区定时推送每日计划。
- **移动端体验**：响应式布局、底部导航、PWA manifest、favicon 和 iOS 主屏幕图标。
- **自动化部署**：GitHub Actions 监听 main 分支，SSH 连接阿里云服务器并执行生产部署脚本。

## 功能模块

### 账号与个人资料

- 用户注册、登录和退出登录
- JWT Bearer Token 鉴权与 Argon2 密码哈希
- 维护身体资料、健身目标和体重数据
- 按用户隔离个人资料、计划、记录和聊天上下文

### 热量与营养计算

- 基础代谢和每日总消耗估算
- 减脂、维持、增肌目标计算
- 每日热量目标
- 蛋白质、碳水、脂肪目标
- 首页实时显示已摄入、运动消耗、剩余热量和完成状态

### 计划管理

- 生成并保存 7 天饮食与训练计划
- 餐食包含预计热量、宏量营养素、食材和大致份量
- 训练包含训练类型、动作、组数、次数和建议
- 计划支持按日期查看，默认展示当天
- 支持延迟训练日
- 支持 AI 教练在保留整体计划框架的情况下调整单个餐食或局部训练
- AI 不可用时可使用确定性模板计划降级生成

### 饮食与运动记录

- 单独记录饮食和运动
- 自然语言解析食物、份量、运动类型、时长和训练信息
- 混合输入自动拆分饮食和运动
- 自动估算食物热量、蛋白质、碳水、脂肪和运动消耗
- 首页活动消耗汇总
- 饮食记录支持编辑、删除和撤销，运动记录支持撤销
- 记录使用真实创建时间，展示小时和分钟

### AI 教练

- 支持 OpenAI-compatible API
- 支持自定义 AI_BASE_URL、AI_API_KEY 和 AI_MODEL
- 读取当前用户资料、目标、生效计划、今日记录、近期聊天和重要计划调整
- 聊天记录保存到数据库，窗口自动滚动到最新消息
- Markdown 内容渲染为标题、列表、加粗和提示内容
- 支持删除单条聊天记录和清空聊天记录
- 支持饮食替换、训练调整、记录解释和局部计划修改

### 钉钉通知

- 用户在“我的”页面配置自己的钉钉群机器人 Webhook
- 支持自定义关键词、加签密钥、配置状态和测试推送
- 敏感凭据使用 Fernet 加密后保存
- 后端定时任务按中国标准时间发送每日计划
- 支持全局环境变量作为可选默认配置

## 技术栈

### 前端

React 19、TypeScript、Vite 7、React Testing Library、Vitest、CSS 响应式布局、PWA manifest、iOS Home Screen metadata。

### 后端

Python 3.11+、FastAPI、Uvicorn、SQLAlchemy 2、Alembic、PostgreSQL、psycopg、Pydantic Settings、Argon2-CFFI、Cryptography/Fernet、HTTPX、APScheduler、Pytest、Ruff。

### 部署与运维

Docker Compose、PostgreSQL 16、Nginx、1Panel/OpenResty、阿里云 ECS、GitHub Actions、SSH 自动部署。

## 项目结构

    fitplan-ai/
    ├─ backend/
    │  ├─ app/
    │  │  ├─ api/              REST API 路由
    │  │  ├─ core/             配置、安全和错误处理
    │  │  ├─ db/               数据库会话和 Base
    │  │  ├─ models/           数据库模型
    │  │  ├─ schemas/          Pydantic 请求/响应模型
    │  │  └─ services/         业务服务和第三方集成
    │  ├─ alembic/             数据库迁移
    │  ├─ tests/               后端测试
    │  ├─ Dockerfile
    │  └─ pyproject.toml
    ├─ frontend/
    │  ├─ src/
    │  │  ├─ components/       通用 UI 组件
    │  │  ├─ features/         业务组件
    │  │  ├─ lib/              API 客户端、类型和工具
    │  │  ├─ pages/            首页、计划、记录、AI 教练和我的
    │  │  └─ styles/           全局视觉和响应式样式
    │  ├─ public/               favicon、PWA manifest、iOS 图标
    │  ├─ Dockerfile
    │  ├─ nginx.conf
    │  └─ package.json
    ├─ infra/
    │  ├─ docker-compose.yml   PostgreSQL、backend、web 编排
    │  ├─ nginx.conf            前端路由和 API 反向代理
    │  └─ .env.example          生产环境变量模板
    ├─ scripts/
    │  ├─ dev.ps1
    │  ├─ verify.ps1
    │  └─ deploy-production.sh
    ├─ docs/
    └─ README.md

## 本地开发

### 环境要求

- Python 3.11+
- Node.js 20.19+ 或 22.12+
- pnpm 11.9.0（推荐）
- Docker Desktop（使用完整本地容器环境时）
- PostgreSQL（本地直接运行后端时）

### 配置环境变量

复制环境变量模板：

    Copy-Item infra/.env.example infra/.env

至少需要修改：

    JWT_SECRET=请替换为随机长密钥
    NOTIFICATION_ENCRYPTION_KEY=请替换为另一组随机长密钥
    POSTGRES_PASSWORD=请替换为数据库密码

启用 AI 时配置：

    AI_BASE_URL=https://你的中转站地址/v1
    AI_API_KEY=你的密钥
    AI_MODEL=你的模型名称

启用全局钉钉默认推送时配置：

    DINGTALK_WEBHOOK=你的Webhook
    DINGTALK_SECRET=你的加签密钥
    DINGTALK_DAILY_PUSH_HOUR=8
    DINGTALK_DAILY_PUSH_MINUTE=0

不要把真实的 .env、API Key、Webhook、JWT 密钥或数据库密码提交到 Git。

### 启动后端

    python -m venv .venv
    .\.venv\Scripts\python -m pip install -e ".\backend[test]"
    .\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload

后端默认地址为 http://127.0.0.1:8000，健康检查为 GET /health，返回 {"status":"ok"}。

### 启动前端

    cd frontend
    pnpm install
    pnpm run dev

前端默认地址为 http://127.0.0.1:5173。

常用命令：

    pnpm run test -- --run
    pnpm run build
    pnpm run preview

也可以在仓库根目录运行：

    .\scripts\dev.ps1
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1

## Docker Compose 启动

生产编排会启动 PostgreSQL、FastAPI 后端和 Nginx 前端：

    cp infra/.env.example infra/.env
    docker compose --env-file infra/.env -f infra/docker-compose.yml up -d --build

默认前端只绑定到服务器本机：

    127.0.0.1:18081 -> web:80

这样可以避免和服务器上已有网站占用公网 80/443 端口，再交给 1Panel/OpenResty 做反向代理。

查看服务：

    docker compose --env-file infra/.env -f infra/docker-compose.yml ps
    curl http://127.0.0.1:18081/health

生产环境不要执行 docker compose down -v，否则可能删除 PostgreSQL 持久化卷。

## API 模块

| 模块 | 主要路径 | 作用 |
| --- | --- | --- |
| Auth | /api/auth/* | 注册、登录、当前用户 |
| Profile | /api/profile/* | 身体资料、目标、体重数据 |
| Calorie | /api/calorie/preview | 热量和宏量营养素预览 |
| Records | /api/records/* | 饮食、运动、日报和撤销 |
| Plans | /api/plans/* | 生成、保存、激活、查看和延迟计划 |
| AI | /api/ai/* | AI 对话、上下文和聊天记录管理 |
| Notifications | /api/notifications/dingtalk/* | 钉钉配置、测试和状态 |
| Health | /health | 服务健康检查 |

FastAPI 启动后可通过 http://127.0.0.1:8000/docs 查看自动接口文档。

## 测试与质量检查

后端：

    .\.venv\Scripts\python -m pytest backend -q
    .\.venv\Scripts\python -m ruff check backend

前端：

    cd frontend
    pnpm run test -- --run
    pnpm run build

## 生产部署

项目适合部署到阿里云 ECS + 1Panel：

1. 服务器安装 Docker、Docker Compose 和 OpenResty；
2. 将仓库放到 /opt/fitplan-ai；
3. 在 /opt/fitplan-ai/infra/.env 配置生产变量；
4. 通过 1Panel 创建反向代理，将网站流量转发到 127.0.0.1:18081；
5. 使用 GitHub Actions 监听 main 分支；
6. GitHub Actions 通过 SSH 执行 scripts/deploy-production.sh；
7. 部署脚本执行 Git fast-forward、Compose 校验、镜像构建和服务启动。

详细说明：

- 1Panel / 阿里云 ECS 部署指南：docs/1panel-deploy.md
- GitHub Actions 自动部署指南：docs/github-actions-deploy.md

## 当前边界

- AI 功能依赖可用的 OpenAI-compatible API；未配置时，系统保留明确的配置错误提示，并可使用确定性计划模板完成基础计划生成。
- 热量和运动消耗属于估算值，不能替代医生、营养师或教练的专业建议。
- 项目目前没有在仓库中声明开源许可证，二次分发前请先补充 License。
