# IAM 架构迁移说明

旧版 Keycloak Organizations、受控租户 API、NATS 投影和周期对账迁移流程已退役。当前迁移由 Alembic revision `0021_local_identity` 一次完成，太极 PostgreSQL 成为用户业务记录、租户、成员关系和权限的唯一权威。

升级和回滚步骤统一维护在 [太极统一登录部署与回滚](./iam-deployment.md)，不要再运行旧版 `iam-migrate`、`iam-projector` 或 `iam-reconcile` 命令。

该 Schema 权威迁移与 Docker 到 K8s 的环境数据复制是两件事。首次生产数据复制已经完成，
快照、表计数、文件校验和人工验收见
[`deploy/taiji-k8s/MIGRATION.md`](../../deploy/taiji-k8s/MIGRATION.md)；日常发布不得重新执行全量复制。
