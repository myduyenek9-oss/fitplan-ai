# GitHub Actions 自动部署

当 main 分支收到新提交时，.github/workflows/deploy.yml 会通过 SSH 连接生产服务器，并执行：

    cd /opt/fitplan-ai
    DEPLOY_BRANCH=main bash scripts/deploy-production.sh

工作流不需要额外的启用变量。只要仓库 Secrets 配置完整，每次 push 到 main 都会尝试部署；也可以从 Actions 页面手动运行。

## 一、在服务器创建部署密钥

在 1Panel 的服务器终端执行：

    mkdir -p /root/.ssh
    chmod 700 /root/.ssh
    ssh-keygen -t ed25519 -C "github-actions-fitplan" -f /root/.ssh/fitplan_github_actions -N ""
    cat /root/.ssh/fitplan_github_actions.pub >> /root/.ssh/authorized_keys
    chmod 600 /root/.ssh/authorized_keys
    cat /root/.ssh/fitplan_github_actions

最后一条命令会显示私钥。复制从 BEGIN OPENSSH PRIVATE KEY 到 END OPENSSH PRIVATE KEY 的完整内容，不要将其发送到聊天、提交到 Git 或写进项目 .env。

确认 GitHub Secret 保存成功后，可以删除服务器上的私钥副本，只保留公钥和 authorized_keys：

    rm -f /root/.ssh/fitplan_github_actions

不要删除：

    /root/.ssh/fitplan_github_actions.pub
    /root/.ssh/authorized_keys

## 二、配置 GitHub Secrets

打开 GitHub 仓库：

    Settings → Secrets and variables → Actions → Secrets → New repository secret

添加以下 Secrets：

| 名称 | 值 |
| --- | --- |
| DEPLOY_HOST | 服务器公网 IP，例如 47.99.58.95 |
| DEPLOY_PORT | SSH 端口，通常为 22 |
| DEPLOY_USER | 服务器登录用户，例如 root |
| DEPLOY_SSH_KEY | 上一步复制的完整 OpenSSH 私钥 |

DEPLOY_PORT 是 SSH 端口，不是网站访问端口 18088。

## 三、第一次手动测试

打开仓库的：

    Actions → Deploy FitPlan AI → Run workflow → Run workflow

成功日志最后应包含：

    Deployment finished successfully.

之后每次向 main 分支 push，GitHub Actions 都会立即触发部署。concurrency 配置会避免多个生产部署互相覆盖，服务器端脚本也使用文件锁防止并发执行。

## 四、检查生产服务

服务器端检查：

    cd /opt/fitplan-ai
    docker compose --env-file infra/.env -f infra/docker-compose.yml ps
    curl http://127.0.0.1:18081/health

公网检查：

    curl http://服务器公网 IP:18088/health

## 五、常见问题

### Permission denied (publickey)

检查 DEPLOY_SSH_KEY 是否包含完整私钥，且对应的公钥内容已追加到 /root/.ssh/authorized_keys。

### Connection timed out

检查阿里云安全组是否允许 TCP 22，以及服务器 SSH 服务是否运行：

    systemctl status ssh --no-pager
    ss -lntp | grep ':22'

### 部署成功但页面没有变化

先检查 Actions 日志是否拉取到了最新提交，再清理浏览器缓存。iPhone 主屏幕图标有独立缓存，通常需要删除旧快捷方式后重新添加。

### 部署失败但页面仍然可以访问

不要执行 docker compose down -v。先查看容器日志和磁盘空间，确认 PostgreSQL 持久化卷没有被删除：

    docker compose --env-file infra/.env -f infra/docker-compose.yml ps
    docker compose --env-file infra/.env -f infra/docker-compose.yml logs --tail=100 web backend
