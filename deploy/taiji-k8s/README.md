# Taiji Kubernetes 部署

本目录使用 Kustomize 将 Taiji 部署到 `lihao` 命名空间。业务组件只创建
`ClusterIP`，由集群内的 `frpc` 将 `evaluation.fangcunleap.com` 转发到前端。
`taiji.lihao.fun` 保留给本机 Docker 开发环境。

## 前提

- 使用 `deploy/taiji-docker/.env` 生成集群 Secret，真实密钥不提交 Git。
- `02-secret.example.yaml` 仅用于说明字段，不包含在 Kustomize 资源中，不要直接应用。
- 所有镜像都位于 `harbor.aixiongan.org.cn:9443/lihao`。
- `taiji-frpc-config` Secret 从现有方寸 FRP 配置生成，不提交 Git。
- 复用现有 RWX PVC `pvc-gpfshome-lihao` 保存任务日志和 HuggingFace 缓存。
- PostgreSQL、Redis 使用 `rancher-local-path` PVC，仅适合当前单节点绑定部署；
  节点故障恢复能力需要在生产切换前另行解决。

## 命令

```bash
make k8s-validate
make k8s-sync-images
make k8s-build-push
FRPC_SOURCE_CONFIG=/secure/path/frpc.toml make k8s-frpc-secret
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

Docker 到 K8s 的首次生产数据复制会替换 K8s 中的 `taiji`、`keycloak` 两个数据库，
并完整复制 `app_data` 与 `app_logs`。脚本会先备份 K8s 目标数据，停止 Docker 写入，
校验所有表的行数和文件 SHA-256，并在失败时自动恢复 Docker 应用：

```bash
CONFIRM_TAIJI_PRODUCTION_MIGRATION=docker-to-k8s make k8s-migrate-data
```

迁移成功后 Docker 应用仍保持停止，直到 FRP 切换和生产验证完成。Redis 会话、任务队列
和可重建的 `hf_cache` 不迁移。迁移后 Docker 开发环境与 K8s 生产环境数据独立，不再同步。

首次生产迁移的实际结果和回滚边界见 [MIGRATION.md](./MIGRATION.md)。

查看首次平台管理员密码：

```bash
kubectl -n lihao logs job/taiji-iam-bootstrap
```

删除工作负载和新建的本地 PVC：

```bash
make k8s-delete
```

`taiji-secrets` 和现有 `pvc-gpfshome-lihao` 不会被该命令删除。
