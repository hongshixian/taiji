# 太极统一登录部署与回滚

## 当前环境

| 环境 | 入口 | 部署方式 | 数据边界 |
|---|---|---|---|
| 开发 | `https://taiji.lihao.fun` | 本机 Docker Compose + 本机 FRP | 独立 PostgreSQL、文件和 Keycloak |
| 生产 | `https://evaluation.fangcunleap.com` | Kubernetes + 集群内 `taiji-frpc` | 独立 PostgreSQL、PVC 和 Keycloak |

每套环境都通过同一个 Origin 提供 SPA、`/api/` 和 `/iam/`。不要把 Keycloak 单独发布到
另一个公网域名，也不要让同一域名同时指向 Docker 和 K8s。

## 发布门禁

- 备份 Taiji 与 Keycloak 两个 PostgreSQL 逻辑数据库，以及 `app_data`、`app_logs`。
- 生产必须使用随机 `SECRET_KEY`、`TAIJI_OIDC_CLIENT_SECRET`、Keycloak 基础设施管理员密码
  和 PostgreSQL 密码。`JWT_SECRET_KEY` 只供 `AUTH_MODE=legacy` 回滚模式使用，但当前
  K8s Secret 生成脚本仍要求它是非默认强值，以保证回滚路径可用。
- `TAIJI_PUBLIC_URL` 是当前环境主地址；`TAIJI_PUBLIC_URLS` 是允许触发登录回调的 Origin
  白名单，至少包含主地址，值之间用逗号分隔且不能带路径。
- `IAM_PUBLIC_URL` 必须等于 `<TAIJI_PUBLIC_URL>/iam`；容器或 Pod 内的
  `IAM_INTERNAL_URL` 为 `http://keycloak:8080/iam`。
- HTTPS 环境设置 `SESSION_COOKIE_SECURE=true`。FRP 或外层代理必须传递可信的
  `Host` 和 `X-Forwarded-Proto=https`。
- Keycloak、Backend、PostgreSQL 和 Redis 只在内部网络提供服务，公网只连接 Frontend。

## Docker 开发环境

```bash
cp deploy/taiji-docker/.env.example deploy/taiji-docker/.env
# 配置 https://taiji.lihao.fun、随机 Secret 和本机 FRP
make docker-build
make iam-test
make docker-up
docker compose --env-file deploy/taiji-docker/.env \
  -f deploy/taiji-docker/docker-compose.yml ps
make iam-smoke
```

Compose 启动 PostgreSQL、Redis、Keycloak 数据库初始化、Keycloak、一次性 IAM 引导、
Backend、Worker 和 Frontend。只有 Frontend 映射宿主机端口，当前默认是 `28080`。

全新 Realm 中，`iam-bootstrap` 创建用户名 `admin`，生成随机临时密码并要求首次登录修改。
密码只显示一次：

```bash
make iam-bootstrap-password
```

`KEYCLOAK_BOOTSTRAP_ADMIN_USERNAME` 是基础设施管理员，不能代替太极平台管理员登录业务。
如果 Realm 中已有 `admin` 但没有引导完成标记，引导任务会拒绝覆盖该账号。

## Kubernetes 生产环境

先确认 `deploy/taiji-k8s/01-configmap.yaml` 中的唯一公网地址是
`https://evaluation.fangcunleap.com`，并让三个自定义镜像标签指向同一次发布：

```bash
make k8s-validate
make k8s-sync-images                    # 首次或公共镜像版本变化时
IMAGE_TAG=<git-sha> make k8s-build-push
# 更新清单中的 taiji-backend、taiji-frontend、taiji-keycloak 标签
FRPC_SOURCE_CONFIG=/secure/path/frpc.toml make k8s-frpc-secret
make k8s-deploy
make k8s-status
```

`make k8s-deploy` 会从忽略提交的 `deploy/taiji-docker/.env` 幂等生成
`taiji-secrets`，重建 `taiji-iam-bootstrap` Job，并应用整套 Kustomize 清单。
FRP 配置单独保存在 `taiji-frpc-config` Secret 中，不会提交到 Git。

业务组件均为 `ClusterIP`。`taiji-frpc` 在集群内连接 `frontend:80`；Frontend 再将
`/api/` 和 `/iam/` 分别代理到 Backend 与 Keycloak。详细资源、存储和内部验证命令见
[`deploy/taiji-k8s/README.md`](../../deploy/taiji-k8s/README.md)。

## 发布验证

```bash
curl -fsS "$TAIJI_PUBLIC_URL/api/ready"
curl -fsS "$TAIJI_PUBLIC_URL/iam/realms/fangcun/.well-known/openid-configuration"
```

浏览器验证：

1. 登录或注册在同页输入用户名和密码，并自动回到太极。
2. 首次登录自动创建个人空间，且用户拥有完整租户业务权限。
3. Header 可切换到已有企业租户；个人空间与企业租户任务互相隔离。
4. 平台管理员可创建企业租户并指定初始管理员。
5. 租户管理员可加入已经完成首次登录的全局用户。
6. 成员或角色状态变化后，已有会话在下一次请求刷新权限。
7. 账号中心可以修改密码；退出会同时清理太极会话并结束 Keycloak 登录。

## Schema 与数据迁移

Backend 启动前的 init container/entrypoint 执行 `flask db upgrade`。当前身份权威边界迁移是
`0021_local_identity`，它删除旧 IAM 投影字段和事件表，因此升级旧架构前必须备份。

Docker 到 K8s 的一次性生产数据复制已经在 2026-08-21 完成。实际快照、表计数、文件校验、
登录验收和回滚边界见 [`deploy/taiji-k8s/MIGRATION.md`](../../deploy/taiji-k8s/MIGRATION.md)。
两套环境此后不再同步，禁止再次把开发库直接覆盖生产库。

## 回滚

代码和镜像可以回退，但 `0021_local_identity` 不支持直接 Alembic downgrade。需要回滚身份
权威迁移时，必须停止写入并同时恢复同一时间点的 Taiji 数据库、Keycloak 数据库、应用文件
和对应镜像，不能只恢复其中一项。

生产已经产生新写入后，不能仅把 FRP 切回 Docker，否则会丢失 K8s 新数据。回滚前记录镜像
摘要、Git commit、Alembic revision 和表计数；先在内部端口验证，再恢复 FRP 流量。
