# 太极统一登录部署与回滚

## 发布门禁

- 备份太极与 Keycloak 两个 PostgreSQL 数据库，以及 `app_data`、`app_logs`。
- 生产环境必须设置随机 `SECRET_KEY`、`JWT_SECRET_KEY`、`TAIJI_OIDC_CLIENT_SECRET`、Keycloak 管理密码和 PostgreSQL 密码。
- `TAIJI_PUBLIC_URL` 必须是浏览器可访问的 HTTPS 地址。
- `IAM_PUBLIC_URL` 必须等于主平台地址加 `/iam`；`IAM_INTERNAL_URL` 在容器网络中为 `http://keycloak:8080/iam`。
- HTTPS 环境设置 `SESSION_COOKIE_SECURE=true`，FRP 或外层代理传递可信的 `X-Forwarded-Proto=https`。

## Docker 发布

```bash
cp deploy/taiji-docker/.env.example deploy/taiji-docker/.env
# 编辑 Secret 与公网 URL
make docker-build
make iam-test
make docker-up
docker compose --env-file deploy/taiji-docker/.env \
  -f deploy/taiji-docker/docker-compose.yml ps
./scripts/iam-smoke.sh
```

Compose 运行 PostgreSQL、Redis、Keycloak、一次性登录引导、Backend、Worker 和 Frontend。只有 Frontend 映射宿主机端口，Keycloak 通过 Frontend 的 `/iam/` 访问。

首次部署通过以下命令读取一次性 `admin` 临时密码：

```bash
make iam-bootstrap-password
```

## Kubernetes 发布

```bash
make k8s-validate
make k8s-sync-images
IMAGE_TAG=<git-sha> make k8s-build-push
make k8s-deploy
```

清单只创建 `ClusterIP`。FRP 应指向 Frontend 服务入口，不能分别暴露 Keycloak。发布旧架构升级时，确认旧 `taiji-nats`、`taiji-iam-proxy` 和 `taiji-iam-projector` 工作负载已删除。

## 发布验证

```bash
curl -fsS "$TAIJI_PUBLIC_URL/api/ready"
curl -fsS "$TAIJI_PUBLIC_URL/iam/realms/fangcun/.well-known/openid-configuration"
```

浏览器验证以下流程：

1. 注册账号并自动回到太极。
2. 首次登录自动创建个人空间，且拥有租户管理员权限。
3. 平台管理员创建企业租户并指定初始管理员。
4. 租户管理员加入已有用户，用户在 Header 切换租户。
5. 角色或成员状态修改后旧会话权限立即更新。
6. 账号中心可以修改密码，退出后本地与 Keycloak 会话均结束。

## 数据库迁移

`flask db upgrade` 会执行 `0021_local_identity`。该迁移删除旧投影字段和事件表，因此发布前必须完成数据库备份。迁移完成后核对：

```sql
SELECT count(*) FROM users WHERE keycloak_subject IS NOT NULL;
SELECT tenant_type, count(*) FROM tenants GROUP BY tenant_type;
SELECT count(*) FROM tenant_memberships;
```

用户、租户和成员关系数量必须与升级前业务数据核对结果一致。

## 回滚

代码提交可以回退，但 `0021` 是数据权威边界迁移，不支持直接 Alembic downgrade。回滚必须在停写后同时恢复发布前的太极数据库备份、对应应用镜像和 Keycloak 数据库备份，不能只恢复其中一项。

回滚前记录镜像摘要、Git commit、Alembic revision 和表计数。恢复完成后先在内部端口验证旧版本，再恢复 FRP 流量。
