# Docker 到 K8s 首次生产迁移记录

## 环境边界

- `https://taiji.lihao.fun` 指向本机 Docker，作为开发环境。
- `https://evaluation.fangcunleap.com` 通过 K8s 内的 `taiji-frpc` 指向生产环境。
- 两套环境在 2026-08-21 完成一次性全量复制，之后数据库和用户密码变化不再同步。
- 按迁移决策，生产与开发暂时复用现有部署密钥；后续应安排生产密钥轮换。

## 迁移快照

- 快照目录：`/vol1/1002/git/taiji-backups/production-migration-20260821-093127`
- 业务数据：5 个用户、6 个租户、10 个租户成员关系、3 个模型配置、113 个任务。
- 身份数据：8 个 Keycloak 用户实体、6 条密码凭据、2 个 Realm、16 个 Client。
- 文件数据：255 个文件，归档大小 12,013,274 字节。
- 未迁移：Redis 会话与任务队列、可重建的 `hf_cache`。

快照目录权限为 `0700`，数据库备份与文件归档包含身份凭据和模型 API Key，不得上传到 Git
或复制到非受控位置。

## 验证结果

- `taiji` 和 `keycloak` 的源端、目标端全部表行数在服务启动前完全一致。
- `app_data`、`app_logs` 的所有文件 SHA-256 完全一致。
- 113 条历史任务的日志引用在 K8s 中全部可解析并访问。
- K8s 数据库迁移版本为 `0021_local_identity`。
- 生产 OIDC issuer 为 `https://evaluation.fangcunleap.com/iam/realms/fangcun`。
- 生产 OIDC Client 仅允许 `evaluation.fangcunleap.com` 回调与 Web Origin。
- K8s 后端、Keycloak、Worker、前端、PostgreSQL、Redis 和 FRP 均已就绪。
- 公网健康检查、OIDC 跳转和同页用户名密码表单已通过。
- 用户已完成生产登录验收；默认进入个人空间时任务列表为空，符合租户隔离预期。
- 切换到历史企业租户后，已确认历史任务及相关业务数据可见。

## 回滚边界

生产环境已经完成真实登录和业务数据验收，应按已经产生新写入处理，不得直接切回 Docker，
否则会丢失 K8s 新数据。必须先停止生产写入，
备份 K8s 的 `taiji`、`keycloak`、`app_data` 和 `app_logs`，再执行反向迁移或修复后继续使用 K8s。
