# IAM 旧数据迁移操作手册

本手册用于把太极本地用户、租户和成员关系一次性导入 Keycloak。迁移保留所有业务表主键和旧密码摘要，在灰度期仍可切回 `AUTH_MODE=legacy`。

## 安全边界

- 迁移接口默认关闭，仅当 Keycloak 的 `IAM_MIGRATION_ENABLED=true` 时存在。
- 接口只接受 `taiji-migrator` confidential client 的 service-account token。
- 迁移密钥必须使用独立随机 Secret，不得复用 Web、基础设施管理员或对账客户端密钥。
- 旧密码摘要只通过 TLS 发送到迁移接口，不写入迁移账本、错误信息或普通日志。
- Keycloak 首次成功验证旧密码后自动改写为当前 Realm 密码算法。
- 迁移窗口结束前保留本地 `password_hash`；确认不再回滚后另行清理。

## 迁移前

1. 备份太极 PostgreSQL、Keycloak PostgreSQL 和任务文件目录。
2. 先在生产数据脱敏副本上完成全量演练和回滚演练。
3. 配置随机 `TAIJI_MIGRATOR_CLIENT_SECRET`，并保证 Keycloak 与后端使用同一个值。
4. 部署代码并执行 `flask db upgrade`，确认数据库版本为 `0020_iam_event_ledger`。
5. 导入期间保持现有认证入口，暂不切换前端。

## 只读预检

```bash
docker compose --env-file deploy/taiji-docker/.env -f deploy/taiji-docker/docker-compose.yml exec backend flask --app run:app iam-migrate
```

预检不会生成稳定 ID 或迁移账本。以下问题会阻止执行：

- 用户名或邮箱存在忽略大小写冲突。
- 旧密码不是受支持的 Werkzeug `scrypt`/`pbkdf2` 格式。
- 有效租户没有有效管理员。
- 已存在的 IAM 稳定 ID 不是 UUID。
- 本地固定 `admin`/`user` 角色缺失。

自定义角色成员不会阻止迁移，但会明确报告并统一映射为 `member`。

## 执行

临时启用迁移接口并等待 Keycloak 健康：

```bash
IAM_MIGRATION_ENABLED=true docker compose --env-file deploy/taiji-docker/.env \
  -f deploy/taiji-docker/docker-compose.yml up -d --no-deps \
  --force-recreate --wait --wait-timeout 180 keycloak
```

执行迁移：

```bash
docker compose --env-file deploy/taiji-docker/.env -f deploy/taiji-docker/docker-compose.yml exec backend flask --app run:app iam-migrate --apply
```

迁移顺序固定为历史企业租户、用户与个人空间、企业成员关系。每个实体单独提交，并在 `iam_migration_records` 记录状态和重试次数；修复失败原因后执行同一命令即可续跑，已成功实体默认跳过。

本地有效超级管理员且用户名等于 `ADMIN_USERNAME` 时，允许绑定 Keycloak Bootstrap 创建的同名 `admin`，但不会覆盖其随机临时密码。其他既有 IAM 账号冲突必须逐个显式确认：

```bash
docker compose --env-file deploy/taiji-docker/.env -f deploy/taiji-docker/docker-compose.yml exec backend flask --app run:app iam-migrate --apply \
  --link-existing exact_username \
  --link-existing user@example.com
```

受控对账时可用 `--force` 重交已成功实体。该选项不是常规迁移所需参数。

## 验证与关闭

开发或隔离测试环境可运行真实首次登录验证：

```bash
make iam-migration-integration-test
```

生产核对至少包括：

- 用户、历史企业租户和历史成员数量与迁移前一致。
- 每个用户都有一个受保护的个人空间及 `tenant_admin` membership。
- 历史 `guest` 成为受保护企业租户，原业务数据的 `tenant_id` 未改变。
- 原管理员/owner 为 `tenant_admin`，其他及自定义角色成员为 `member`。
- 有效 `is_superuser` 用户获得 `platform_admin`。
- 抽样普通用户可用旧密码首次登录，随后 Keycloak credential 不再是 `taiji-legacy`。
- 重跑命令不会创建重复用户、Organization 或 membership。

完成后必须关闭迁移接口：

```bash
docker compose --env-file deploy/taiji-docker/.env \
  -f deploy/taiji-docker/docker-compose.yml up -d --no-deps --force-recreate \
  --wait --wait-timeout 180 keycloak
```

确认容器环境中的 `IAM_MIGRATION_ENABLED=false`，并验证迁移 URL 返回 `404`。随后才能开始 OIDC 灰度切换。

OIDC 切换、事件投影和发布检查按 [IAM 部署与回滚](./iam-deployment.md) 执行。

## 回滚

- OIDC 灰度异常时将太极切回 `AUTH_MODE=legacy`，不要删除已导入的 Keycloak 对象或稳定 ID。
- `iam_migration_records` 和本地 IAM 投影字段可保留，后续续跑仍保持幂等。
- 只有在确认不再回滚后，才安排单独变更清理本地密码字段和 Legacy Password Provider。
