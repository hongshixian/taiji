# Taiji Kubernetes 部署

本目录使用 Kustomize 将 Taiji 部署到 `lihao` 命名空间。当前版本只创建
`ClusterIP`，不包含 Ingress、NodePort 或 FRP 配置。

## 前提

- 使用 `deploy/taiji-docker/.env` 生成集群 Secret，真实密钥不提交 Git。
- `02-secret.example.yaml` 仅用于说明字段，不包含在 Kustomize 资源中，不要直接应用。
- 所有镜像都位于 `harbor.aixiongan.org.cn:9443/lihao`。
- 复用现有 RWX PVC `pvc-gpfshome-lihao` 保存任务日志和 HuggingFace 缓存。
- PostgreSQL、Redis 使用 `rancher-local-path` PVC，仅适合当前单节点绑定部署；
  节点故障恢复能力需要在生产切换前另行解决。

## 命令

```bash
make k8s-validate
make k8s-sync-images
make k8s-build-push
make k8s-deploy
make k8s-status
```

自定义镜像默认使用清单中的固定标签。发布新的应用代码时，通过 `IMAGE_TAG` 指定新标签，
并同步更新清单中的 Backend、Frontend 和 Keycloak 三个自定义镜像标签后再部署；Worker 复用 Backend 镜像。

部署命令会从 Docker `.env` 幂等创建 `taiji-secrets`，然后统一执行
`kubectl apply -k deploy/taiji-k8s`。登录引导 Job 每次发布前会删除并重建，
以便幂等校正 Realm 配置。

内部验证：

```bash
kubectl -n lihao port-forward service/frontend 28081:80
curl http://127.0.0.1:28081/api/ready

curl http://127.0.0.1:28081/iam/realms/fangcun
```

当前清单初始化全新 PostgreSQL 数据卷，不会复制或修改 Docker Compose 的
`pg_data`。确认组件运行稳定后，再安排停写、备份和数据迁移。OIDC 浏览器登录需等
FRP 接入后验证。

查看首次平台管理员密码：

```bash
kubectl -n lihao logs job/taiji-iam-bootstrap
```

删除工作负载和新建的本地 PVC：

```bash
make k8s-delete
```

`taiji-secrets` 和现有 `pvc-gpfshome-lihao` 不会被该命令删除。
