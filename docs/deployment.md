# 部署操作清单（VPS: 103.40.204.95，域名: aisearch.acuventech.com）

本项目走 ghcr.io 镜像 + GitHub Actions SSH 自动部署，与同一台 VPS 上的 erp_os/crm_os
共用 `vps_infra` 栈（Nginx 容器、proxy_net/data_net 网络、统一证书管理、infra_mysql）。

以下步骤需要你手动在 VPS 和 GitHub 上各执行一次（首次上线）。之后每次 push 到 main
分支会自动构建镜像并部署。

## 1. 在共享 MySQL 创建只读账号

仓库根目录的 [setup_readonly_user.sql](../setup_readonly_user.sql) 已包含建账号语句。
在 VPS 上对 `infra_mysql` 容器执行：

```bash
docker exec -i infra_mysql mysql -uroot -p < /path/to/setup_readonly_user.sql
```

确认账号可从其他容器（同 data_net）连接：

```bash
docker exec -it infra_mysql mysql -u ai_readonly -p123456 -h infra_mysql -e "SHOW DATABASES;"
```

> 如果密码需要更换，同步执行 [reset_readonly_password.sql](../reset_readonly_password.sql)，
> 并更新 `.env` 里的 `CRM_DB_PASSWORD` / `ERP_DB_PASSWORD`。

## 2. 首次拉取代码并配置 .env

```bash
sudo mkdir -p /opt/ai_search_os
cd /opt/ai_search_os
git clone https://github.com/kelvinpang90/ai_search_os.git .
cp .env.production.example .env
vim .env   # 填入 ANTHROPIC_API_KEY、ai_readonly 密码、确认 GHCR_OWNER=kelvinpang90
```

## 3. 配置 Nginx 反代

把 [nginx/conf.d/aisearch.conf](../nginx/conf.d/aisearch.conf) 复制到 vps_infra 的
Nginx 容器挂载目录：

```bash
cp /opt/ai_search_os/nginx/conf.d/aisearch.conf /srv/infra/nginx/conf.d/aisearch.conf
docker exec infra_nginx nginx -s reload   # 容器名以实际为准
```

证书走现有的统一证书管理（与 erp.kelvinpeng.com 等共用同一套 `/etc/nginx/certs/origin.*`），
无需为新域名单独申请——只要该域名已被现有证书（或泛域名证书）覆盖。如未覆盖，需先把
`aisearch.acuventech.com` 加入证书 SAN 列表，重新签发后再继续。

## 4. 首次手动起容器（验证镜像与网络是否打通）

```bash
cd /opt/ai_search_os
docker login ghcr.io -u kelvinpang90   # 用具备 read:packages 权限的 PAT
docker compose pull
docker compose up -d
docker compose logs -f aisearch_backend   # 确认健康检查通过、能连上 infra_mysql
curl -fsS http://aisearch.acuventech.com/health
```

## 5. 在 GitHub 仓库添加 Secrets

仓库 `kelvinpang90/ai_search_os` → Settings → Secrets and variables → Actions，
新增（与 erp_os 共用同一台 VPS，取值应与 erp_os 仓库里的一致）：

| Secret 名 | 说明 |
|---|---|
| `VPS_HOST` | `103.40.204.95` |
| `VPS_USER` | SSH 登录用户名 |
| `VPS_SSH_KEY` | SSH 私钥（与 erp_os 部署用的同一把，或新建一把授权到该用户） |
| `VPS_PORT` | SSH 端口 |
| `AISEARCH_PUBLIC_URL` | `https://aisearch.acuventech.com`（用于部署后烟雾测试，可选） |

> 这些是仓库级 Secret，不会从 erp_os 自动继承，需要在本仓库单独添加一遍。

## 6. 触发首次自动部署

推送到 `main` 分支即可触发 [.github/workflows/deploy.yml](../.github/workflows/deploy.yml)，
或在 Actions 页面手动 `workflow_dispatch` 一次，确认整条流水线（构建镜像 → 推送 ghcr.io →
SSH 部署 → 健康检查）跑通。

## 日常运维

- 查看日志：`docker compose -f /opt/ai_search_os/docker-compose.yml logs -f aisearch_backend`
- 手动重新拉取部署：参考 erp_os 的 [scripts/deploy.sh](../../erp_os/scripts/deploy.sh) 改写（本项目无数据库迁移，跳过 alembic 步骤）
- 排查 502：先看 `aisearch_backend` 是否 healthy，再看 Nginx 容器是否能解析到 `aisearch_backend:8000`（同 proxy_net）
