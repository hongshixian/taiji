# IAM 架构迁移说明

旧版 Keycloak Organizations、受控租户 API、NATS 投影和周期对账迁移流程已退役。当前迁移由 Alembic revision `0021_local_identity` 一次完成，太极 PostgreSQL 成为用户业务记录、租户、成员关系和权限的唯一权威。

升级和回滚步骤统一维护在 [太极统一登录部署与回滚](./iam-deployment.md)，不要再运行旧版 `iam-migrate`、`iam-projector` 或 `iam-reconcile` 命令。
