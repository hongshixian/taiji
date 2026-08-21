# Taiji Kubernetes 部署

本目录通过 Kustomize 将太极生产环境部署到 `lihao` 命名空间。生产入口是
`https://evaluation.fangcunleap.com`；`https://taiji.lihao.fun` 保留给本机 Docker
开发环境。两套环境数据独立，不会自动同步。

## 网络拓扑

```text
Internet -> FRP server -> taiji-frpc Pod -> frontend:80
                                      /api/ -> backend:5000
                                      /iam/ -> keycloak:8080/iam

backend/worker -> postgres:5432
backend/worker -> redis:6379
backend        -> keycloak:8080/iam
```

Backend、Frontend、Keycloak、PostgreSQL 和 Redis Service 都是 `ClusterIP`。K8s 不使用
Ingress，也不为这些组件创建 NodePort 或 LoadBalancer；公网流量只能从 `taiji-frpc`
进入 Frontend 网关。

## 资源

| 类型 | 名称 | 用途 |
|---|---|---|
| Deployment | `taiji-backend` | Flask/Gunicorn API；init container 执行 Alembic |
| Deployment | `taiji-worker` | Celery 测评任务 |
| Deployment | `taiji-frontend` | Vue 静态文件与统一 Nginx 网关 |
| Deployment | `taiji-keycloak` | 太极专用登录内核 |
| Deployment | `taiji-frpc` | 生产域名 FRP 客户端 |
| StatefulSet | `taiji-postgres` | Taiji 与 Keycloak 两个逻辑数据库 |
| StatefulSet | `taiji-redis` | BFF 会话、限流和 Celery |
| Job | `taiji-iam-bootstrap` | Realm、OIDC Client 和首次管理员幂等校正 |
| PVC | `taiji-postgres-data`、`taiji-redis-data` | 单节点本地持久化 |
| Existing PVC | `pvc-gpfshome-lihao` | `app_data`、`app_logs` 和 HuggingFace 缓存 |

现有 RWX PVC 不由本目录创建。`rancher-local-path` 的 PostgreSQL/Redis PVC 依赖当前节点，
节点故障恢复能力仍需通过备份或外部存储解决。

集群中目前还保留旧架构的 `taiji-nats-data` PVC，但没有 NATS 工作负载使用它，也不在本
Kustomize 清单中。它不会被 `make k8s-delete` 删除；确认不再需要历史数据后再单独清理。

## Secret 与镜像

- `taiji-secrets` 从忽略提交的 `deploy/taiji-docker/.env` 生成。
- `taiji-frpc-config` 从已有 FRP TOML 配置生成。
- `02-secret.example.yaml` 只列出字段，不在 Kustomize resources 中，不能直接用于生产。
- 所有镜像来自 `harbor.aixiongan.org.cn:9443/lihao`，集群不依赖公共镜像仓库。
- Worker 与 Backend 复用同一个应用镜像。

Secret、数据库备份、FRP token 和模型 API Key 不得提交到 Git。

## 首次准备

```bash
make k8s-validate
make k8s-sync-images
IMAGE_TAG=<git-sha> make k8s-build-push
FRPC_SOURCE_CONFIG=/secure/path/frpc.toml make k8s-frpc-secret
```

`k8s-sync-images` 同步 PostgreSQL 16、Redis 7、Nginx 和 FRP 0.69.0。只有首次部署或公共
镜像版本变化时需要执行。构建完成后，必须把 Backend、Frontend、Keycloak 清单中的标签
更新为这次发布的实际标签；Worker 和 Backend 标签保持一致。

## 发布

```bash
make k8s-validate
make k8s-deploy
make k8s-status

kubectl -n lihao rollout status deployment/taiji-keycloak
kubectl -n lihao wait --for=condition=complete job/taiji-iam-bootstrap --timeout=300s
kubectl -n lihao rollout status deployment/taiji-backend
kubectl -n lihao rollout status deployment/taiji-worker
kubectl -n lihao rollout status deployment/taiji-frontend
kubectl -n lihao rollout status deployment/taiji-frpc
```

`make k8s-deploy` 会幂等生成 `taiji-secrets`、删除旧 bootstrap Job 并执行一次
`kubectl apply -k deploy/taiji-k8s`。它不会生成 FRP Secret，也不会自动修改镜像标签。

## 验证

集群内部验证：

```bash
kubectl -n lihao port-forward service/frontend 28081:80
curl -fsS http://127.0.0.1:28081/api/ready
curl -fsS http://127.0.0.1:28081/iam/realms/fangcun/.well-known/openid-configuration
```

公网验证：

```bash
curl -fsS https://evaluation.fangcunleap.com/api/ready
curl -fsS https://evaluation.fangcunleap.com/iam/realms/fangcun/.well-known/openid-configuration
```

随后人工登录，确认默认个人空间、Header 租户切换和企业租户历史任务。当前生产迁移已经
完成上述验收，结果记录在 [MIGRATION.md](./MIGRATION.md)。

全新 Realm 才会在 bootstrap Job 日志中输出一次 `admin` 随机临时密码：

```bash
kubectl -n lihao logs job/taiji-iam-bootstrap
```

已有 Realm 的正常发布只会执行幂等校正，不会重新生成或覆盖管理员密码。

## 已完成的一次性迁移

Docker 到 K8s 的全量复制命令是：

```bash
CONFIRM_TAIJI_PRODUCTION_MIGRATION=docker-to-k8s make k8s-migrate-data
```

该命令已于 2026-08-21 执行完成，只保留作灾难恢复参考，**不得在日常发布中再次运行**。
迁移复制了 `taiji`、`keycloak` 数据库和 `app_data`、`app_logs`，没有迁移 Redis
会话、任务队列和可重建的 `hf_cache`。完整快照和校验结果见 [MIGRATION.md](./MIGRATION.md)。

## 删除与回滚

```bash
make k8s-delete
```

该命令删除 Kustomize 管理的工作负载和新建的本地 PVC，不删除 `taiji-secrets`，也不删除
现有 `pvc-gpfshome-lihao`。这不是无损暂停命令；生产操作前必须确认备份和回滚方案。

生产已经完成登录验收并可能产生新写入，不能只把 FRP 切回旧 Docker 数据。完整回滚要求见
[统一登录部署与回滚](../../docs/operations/iam-deployment.md)。
