# FitPlan AI：阿里云 ECS + 1Panel 部署指南

适用目标：在已经运行其他网站的阿里云 ECS 上部署 FitPlan AI，并通过 Git 仓库自动更新。

## 一、推荐架构

```text
域名（推荐）或独立公网端口
          ↓
1Panel / OpenResty（监听公网 80、443 或独立端口）
          ↓
http://127.0.0.1:18081
          ↓
FitPlan web 容器（前端 Nginx）
          ↓ /api、/health
FastAPI backend 容器
          ↓
PostgreSQL 容器 + Docker 数据卷
```

本项目的 Compose 不再占用宿主机 `80:80`，默认只绑定：

```text
127.0.0.1:18081 -> web 容器的 80
```

因此不会与现有网站争抢 80/443。PostgreSQL 和后端 API 都不直接暴露到公网。

## 二、部署前检查

在 1Panel 中确认：

1. **应用商店**中已经安装并启动 OpenResty。
2. **容器**页面显示 Docker 正常运行。
3. 现有网站和容器没有占用 `18081`。若已占用，在 `infra/.env` 中把 `FITPLAN_HTTP_PORT` 改为其他高位端口，例如 `18082`。
4. 阿里云安全组已开放：
   - 使用域名：TCP `80`、`443`。
   - 暂时只用 IP + 独立端口：再开放你在 1Panel 网站中选择的公网端口，例如 `18088`。
5. 不要开放 PostgreSQL `5432`，也不需要开放后端 `8000` 和内部应用端口 `18081`。

> `18081` 是服务器本机的反向代理目标端口；`18088` 只是“没有域名时”可选的公网访问端口，两者不要混淆。

## 三、把代码放到服务器

### 方案 A：Git 仓库（推荐，可自动部署）

1. 把本项目提交并推送到 GitHub、Gitee、GitLab 或 Codeup。
2. 在 1Panel 的 **主机 → 终端** 中，只执行一次克隆：

```bash
cd /opt
git clone <你的仓库地址> fitplan-ai
cd /opt/fitplan-ai
```

私有仓库推荐使用只读 Deploy Key，不要把 Git 密码或访问令牌写进部署脚本或提交到仓库。

### 方案 B：完全使用文件管理器上传

可以在 **主机 → 文件** 中上传项目压缩包并解压到 `/opt/fitplan-ai`。这种方式可以通过 1Panel 部署，但因为服务器目录不是 Git 工作区，不能使用本文的 Git 自动更新脚本。

## 四、创建生产环境变量

在 1Panel **主机 → 文件** 中：

1. 复制 `/opt/fitplan-ai/infra/.env.example` 为 `/opt/fitplan-ai/infra/.env`。
2. 编辑 `.env`，至少填写：

```env
APP_ENV=production
FITPLAN_HTTP_PORT=18081
JWT_SECRET=<独立长随机值>
NOTIFICATION_ENCRYPTION_KEY=<另一个独立长随机值>
POSTGRES_PASSWORD=<数据库强密码>
AI_BASE_URL=<OpenAI 兼容中转站地址>
AI_API_KEY=<API Key>
AI_MODEL=<中转站实际支持的模型名>
DINGTALK_DAILY_PUSH_HOUR=8
DINGTALK_DAILY_PUSH_MINUTE=0
```

随机值可以在 1Panel Web 终端生成：

```bash
openssl rand -hex 32
```

`JWT_SECRET` 和 `NOTIFICATION_ENCRYPTION_KEY` 应分别生成，不能提交到 Git。`NOTIFICATION_ENCRYPTION_KEY` 用来加密数据库中每位用户保存的钉钉 Webhook/密钥；应用内部会将该字符串派生为 Fernet 密钥，因此使用长随机字符串即可。

如果用户在网页“我的”页面配置自己的钉钉机器人，服务器级 `DINGTALK_WEBHOOK` 和 `DINGTALK_SECRET` 可以留空；这两个变量只作为全局兜底配置。

## 五、使用 1Panel 图形界面创建 Compose

1. 打开 **容器 → 编排 → 创建编排**。
2. 选择 **路径选择**。
3. 选择 `/opt/fitplan-ai/infra/docker-compose.yml`。
4. 编排名称使用 `fitplan-ai`。
5. 确认环境变量文件位于 `/opt/fitplan-ai/infra/.env`。
6. 创建并启动编排。
7. 在编排详情查看 `postgres`、`backend`、`web` 三个容器，等待它们正常运行；`web` 和 `postgres` 应显示健康状态。

首次启动时后端会自动执行 Alembic 数据库迁移。

如果构建失败，在 1Panel 的 **容器 → 编排/容器 → 日志** 中分别查看 `backend` 和 `web` 日志。

## 六、在 1Panel 创建反向代理网站

### 有域名（推荐）

1. 给域名添加 A 记录，指向 `47.99.58.95`。
2. 打开 **网站 → 创建网站 → 反向代理**。
3. 主域名填写你的域名，例如 `fit.example.com`。
4. 代理地址填写：

```text
http://127.0.0.1:18081
```

5. 创建后申请 SSL 证书并启用 HTTPS。

多个网站可以共同使用公网 80/443，OpenResty 会根据域名区分站点，不会冲突。

### 暂时没有域名

同一个公网 IP 的同一个 `80` 端口无法仅靠路径自动区分三个独立网站。建议在 1Panel 新建反向代理网站时使用一个未占用的公网端口，例如：

```text
主域名：47.99.58.95:18088
代理地址：http://127.0.0.1:18081
```

然后在阿里云安全组放行 TCP `18088`，访问：

```text
http://47.99.58.95:18088
```

创建前先在 1Panel 查看网站、容器的端口占用；若 `18088` 已用，换成其他未占用端口。长期公网使用仍建议绑定域名和 HTTPS。

## 七、不手动使用 CLI 的 Git 自动部署

1Panel 可以在图形界面创建 Shell 计划任务。本项目已经提供：

```text
/opt/fitplan-ai/scripts/deploy-production.sh
```

脚本会：

- 使用文件锁避免两个部署任务同时运行；
- 拉取当前分支对应的远端分支；
- 没有新提交时直接结束，不重复构建；
- 只允许 fast-forward 更新，防止意外覆盖服务器修改；
- 校验 Compose 后重新构建和启动；
- 不清理全局 Docker 镜像/卷，避免影响服务器上的另外两个网站；
- 不读取或打印 `.env` 中的密钥。

在 1Panel 中：

1. 打开 **计划任务 → 创建计划任务**。
2. 类型选择 **Shell 脚本**。
3. 名称填写 `FitPlan Git 自动部署`。
4. 周期设置为每 3 分钟，Cron 可使用：

```cron
*/3 * * * *
```

5. 脚本内容填写：

```bash
bash /opt/fitplan-ai/scripts/deploy-production.sh
```

6. 保存后先点击一次“执行”，在执行报告中确认成功。

以后只需要向 Git 仓库 push；服务器通常会在 3 分钟内自动拉取并重新部署。这个方案不需要你日常登录 SSH 或手动输入部署命令，但第一次 clone、配置 Deploy Key 仍需要做一次。

如果生产分支不是服务器当前分支，可以在计划任务中明确指定，例如：

```bash
DEPLOY_BRANCH=main bash /opt/fitplan-ai/scripts/deploy-production.sh
```

## 八、验证

1. 在 1Panel 查看三个容器是否运行。
2. 浏览器打开域名或 `http://47.99.58.95:<公网端口>`。
3. 检查健康接口：`/health` 应返回成功。
4. 完成一次注册、登录、资料保存、AI 对话和计划生成测试。
5. 在“我的”中为测试账号配置钉钉机器人，并执行一次测试推送。

## 九、备份与回滚

### 数据备份

生产数据位于 Compose 的 PostgreSQL Docker volume 中。不要执行：

```bash
docker compose down -v
```

`-v` 会删除数据库卷。建议在 1Panel 创建数据库/目录备份计划，并将备份同步到 OSS 或其他独立存储；还应定期验证备份确实可以恢复。

### 代码回滚

推荐在 Git 仓库对问题提交执行 revert，再 push，让自动部署拉取新的回滚提交。这样服务器和仓库历史保持一致。

如果新版本数据库迁移不可逆，不要只回退应用镜像；需要先根据对应迁移和备份制定数据库回滚方案。

## 十、是否可以完全不用 CLI？

- **首次手动上传部署：可以。** 文件上传、编辑 `.env`、创建 Compose、反向代理和查看日志都能在 1Panel 页面完成。
- **Git push 后自动部署：可以做到日常不用 CLI。** 最实用方式是一次性 clone 仓库，然后使用 1Panel 的 Shell 计划任务调用仓库内脚本。
- **从未执行任何命令且同时要求 Git 自动部署：通常不现实。** 至少需要一次 clone/Deploy Key 初始化；这一步可以在 1Panel 的浏览器终端完成，不需要本地 SSH 客户端。