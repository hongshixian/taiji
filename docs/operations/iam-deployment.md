# IAM 部署与回滚

本手册覆盖 Keycloak IAM、OIDC BFF、NATS 投影消费者和太极前端的发布。旧数据导入细节见 [IAM 旧数据迁移](./iam-migration.md)。

## 发布门禁

- 先在生产脱敏副本完成 `0016 -> 0020 -> 0016 -> 0020` 数据库迁移往返测试。
- 备份太极数据库、Keycloak 数据库、`app_data`、`app_logs` 和 NATS 持久卷。
- 生产 `.env` 必须设置随机 `SECRET_KEY`、`TAIJI_OIDC_CLIENT_SECRET`、`TAIJI_RECONCILER_CLIENT_SECRET`、`TAIJI_MIGRATOR_CLIENT_SECRET`、Keycloak 管理密码、PostgreSQL 密码和 NATS 密码。
- `IAM_PUBLIC_URL`、`TAIJI_PUBLIC_URL` 必须是浏览器可访问的 HTTPS 地址，`SESSION_COOKIE_SECURE=true`。
- 发布前保持 `IAM_MIGRATION_ENABLED=false`；仅在数据导入窗口临时打开。

生产配置使用开发默认 Secret 时，Flask 后端和投影进程会拒绝启动。

## 备份

在维护窗口停止写请求和 Celery 任务后执行，备份文件写到受控目录：

```bash
docker compose exec -T postgres pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB" > taiji-before-iam.dump
docker compose exec -T postgres pg_dump -Fc -U "$POSTGRES_USER" "$KEYCLOAK_DB" > keycloak-before-iam.dump
tar -czf taiji-files-before-iam.tar.gz app_data app_logs
```

记录当前镜像摘要、Git commit、数据库 revision 和各实体数量。不要把数据库备份或 Secret 提交到 Git。

## 发布顺序

1. 构建并测试镜像：

```bash
docker compose build keycloak backend worker frontend
make iam-test
docker compose run --rm --no-deps backend pytest tests/ -q
```

2. 先发布 PostgreSQL、Redis、NATS 和 Keycloak，确认 IAM 扩展健康：

```bash
docker compose up -d --wait postgres redis nats keycloak iam-bootstrap
curl -fsS "$IAM_PUBLIC_URL/realms/fangcun/taiji-iam/health"
```

3. 发布后端以执行 `flask db upgrade`，但旧数据导入完成前保持原认证入口。按迁移手册完成预检、导入、数量核对并关闭迁移 API。

4. 设置 `AUTH_MODE=oidc`，发布后端、投影进程、Worker 和前端：

```bash
docker compose up -d --wait backend iam-projector worker frontend
curl -fsS "$TAIJI_PUBLIC_URL/api/ready"
```

5. 立即执行一次权威全量对账并检查消费者日志：

```bash
make iam-reconcile
docker compose logs --since 10m iam-projector
```

6. 使用非管理员、租户管理员和平台管理员账号分别验证登录、个人空间、企业租户切换、成员管理、任务读写和退出。运行浏览器烟测：

```bash
python3 scripts/oidc-browser-smoke.py \
  --base-url "$TAIJI_PUBLIC_URL" --username smoke-user --password 'test-password'
```

## 运行检查

- `/api/health` 只表示 Flask 进程存活；`/api/ready` 同时检查数据库、Redis 和 IAM 扩展。
- `iam-projector` 使用 JetStream durable consumer `taiji-projection-v1`，成功写入本地投影后才 ACK。
- `iam_event_receipts.event_id` 负责去重，`iam_aggregate_cursors` 记录已处理版本；失败事件保留错误摘要并由 JetStream 重投。
- 投影进程默认每 5 分钟执行全量对账。可用 `make iam-reconcile` 手动修复漏事件。
- 对账只停用或更新身份投影，不删除租户业务数据。
- 关注 `iam.reconciliation.completed` 审计记录、失败 receipt、登录失败率、IAM 5xx、消费者积压和 readiness 状态。

## 回滚

发布后但尚在约定回滚窗口内：

1. 停止 `iam-projector`，防止回滚期间继续更新本地投影。
2. 将应用镜像回退到发布前 commit，并设置 `AUTH_MODE=legacy`。
3. 数据库只回退到应用旧版本能够读取的 revision；不要删除 Keycloak 中已迁移身份，也不要复用或重置稳定 ID。
4. 若数据库迁移本身失败，停止全部写入组件，使用双库备份恢复；不可只恢复其中一个数据库。
5. 修复后重新执行迁移预检、幂等导入和全量对账。

确认不再回滚后，另开变更删除本地密码摘要、旧 JWT 路径和 Legacy Password Provider。该清理不与首次 IAM 切换放在同一发布窗口。
