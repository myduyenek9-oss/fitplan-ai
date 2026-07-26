# GitHub Actions 即时自动部署

当 `main` 分支收到新提交时，`.github/workflows/deploy.yml` 会立即通过 SSH 连接生产服务器，并执行：

```bash
cd /opt/fitplan-ai
DEPLOY_BRANCH=main bash scripts/deploy-production.sh
```

工作流默认由仓库变量 `AUTO_DEPLOY_ENABLED` 控制。只有该变量等于 `true` 时才会实际部署，因此可以先安全地提交工作流，再配置密钥。

## 一、在服务器创建部署密钥

在 1Panel 的服务器终端执行：

```bash
mkdir -p /root/.ssh
chmod 700 /root/.ssh
ssh-keygen -t ed25519 -C "github-actions-fitplan" -f /root/.ssh/fitplan_github_actions -N ""
cat /root/.ssh/fitplan_github_actions.pub >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
cat /root/.ssh/fitplan_github_actions
```

最后一条命令会显示私钥。复制从 `-----BEGIN OPENSSH PRIVATE KEY-----` 到 `-----END OPENSSH PRIVATE KEY-----` 的完整内容，不要将其发送到聊天、提交到 Git 或写进项目 `.env`。

确认 GitHub Secret 保存成功后，可以删除服务器上的私钥副本，只保留公钥和 `authorized_keys`：

```bash
rm -f /root/.ssh/fitplan_github_actions
```

不要删除：

```text
/root/.ssh/fitplan_github_actions.pub
/root/.ssh/authorized_keys
```

## 二、配置 GitHub Secrets

打开 GitHub 仓库：

```text
Settings → Secrets and variables → Actions → Secrets → New repository secret
```

添加以下 Secrets：

| 名称 | 值 |
| --- | --- |
| `DEPLOY_HOST` | `47.99.58.95` |
| `DEPLOY_PORT` | `22` |
| `DEPLOY_USER` | `root` |
| `DEPLOY_SSH_KEY` | 上一步复制的完整 OpenSSH 私钥 |

## 三、开启自动部署

进入：

```text
Settings → Secrets and variables → Actions → Variables → New repository variable
```

创建变量：

```text
Name: AUTO_DEPLOY_ENABLED
Value: true
```

变量创建后，自动部署正式启用。

## 四、第一次手动测试

打开仓库的：

```text
Actions → Deploy FitPlan AI → Run workflow → Run workflow
```

成功日志最后应包含：

```text
Deployment finished successfully.
```

之后每次向 `main` 分支 push，GitHub Actions 都会立即触发部署。`concurrency` 配置会避免多个生产部署互相覆盖，服务器端脚本也使用文件锁防止并发执行。

## 五、检查生产服务

服务器端检查：

```bash
cd /opt/fitplan-ai
docker compose --env-file infra/.env -f infra/docker-compose.yml ps
curl http://127.0.0.1:18081/health
```

公网检查：

```text
http://47.99.58.95:18088/health
```

## 六、常见问题

### 工作流显示 Skipped

检查仓库变量 `AUTO_DEPLOY_ENABLED` 是否准确填写为小写 `true`。

### Permission denied (publickey)

检查 `DEPLOY_SSH_KEY` 是否包含完整私钥，且对应的 `.pub` 内容已追加到 `/root/.ssh/authorized_keys`。

### Connection timed out

检查阿里云安全组是否允许 TCP 22，以及服务器 SSH 服务是否运行：

```bash
systemctl status ssh --no-pager
ss -lntp | grep ':22'
```

### 部署成功但页面没有变化

先检查 Actions 日志是否拉取到了最新提交，再清理浏览器缓存。iPhone 主屏幕图标有独立缓存，通常需要删除旧快捷方式后重新添加。
