# 太极统一登录与租户架构

## 目标边界

Keycloak 是太极进程组内的认证内核，不是独立 IAM 产品，也不向其他业务平台提供认证。系统只有两个权威边界：

- Keycloak：账号凭证、登录会话、密码重置、账号资料和 OIDC 协议。
- 太极 PostgreSQL：用户业务记录、个人空间、企业租户、成员关系、平台管理员、租户管理员、业务角色和权限。

Keycloak Organization、租户 REST 扩展、NATS 事件、投影器和周期对账均不参与当前架构。

## 请求拓扑

```text
Browser / FRP
      |
      v
Taiji frontend gateway :80
  /       -> Vue SPA
  /api/   -> Flask backend:5000
  /iam/   -> Keycloak:8080/iam

Flask -> PostgreSQL (business authority)
Flask -> Redis (BFF session and Celery)
Flask -> Keycloak /iam (OIDC back channel only)
```

外部只暴露前端网关端口。Docker 默认地址为 `http://localhost:28080`；生产主地址为 `https://taiji.lihao.fun`，登录路由随之为 `/iam/`。Kubernetes 中各组件通过 `ClusterIP` 互访，FRP 只需连接 `frontend` 服务入口。

## 登录与注册

1. 浏览器访问 `/api/v1/auth/login` 或 `/register`。
2. Flask 生成 state、nonce 和 PKCE 参数，重定向到同源 `/iam/realms/fangcun/...`。
3. Keycloak 验证账号并把授权码回调到 `/api/v1/auth/callback`。
4. Flask 在服务端兑换令牌；令牌保存在 Redis 服务端会话，不进入浏览器 JavaScript。
5. Flask 按 `keycloak_subject` 查找本地用户。首次登录时原子创建用户、受保护个人空间、owner 成员关系和本地 `admin` 角色。
6. 后续请求只从太极数据库加载租户与业务权限。

Keycloak 的 `platform_admin` Realm Role 仅用于全新部署中第一次创建本地 `admin` 用户。该用户一旦落库，平台管理员状态只由 `users.is_superuser` 管理，之后不会被 Keycloak 角色反向覆盖。

## 租户与权限

- `users` 是全局业务用户，`keycloak_subject` 是登录主体外键。
- `tenants` 保存 `personal` 或 `enterprise` 工作空间。
- `tenant_memberships` 连接用户、租户和本地角色。
- `roles`、`permissions`、`role_permissions` 是业务 RBAC 权威。
- Header 租户下拉框读取当前用户的 active memberships，并用本地 tenant ID 切换。
- 一次浏览器会话只激活一个租户，业务查询由全局 tenant filter 隔离。
- 平台管理员可以创建企业租户、指定首位租户管理员、管理平台管理员。
- 租户管理员可以把已注册且完成首次登录的全局用户直接加入当前租户，无需对方确认。

## 会话安全

- Authorization Code + PKCE、state、nonce 由 Authlib 处理。
- Redis 保存 OIDC token 和太极会话；浏览器只持有 HttpOnly session cookie。
- 写请求必须携带会话内 CSRF token。
- 允许的回调来源严格受 `TAIJI_PUBLIC_URLS` 白名单限制。
- 用户、租户、成员或角色发生本地变更后，请求钩子检测会话快照并立即刷新。
- 密码修改入口跳转 Keycloak Account Console；MFA 当前未启用。

## 历史数据

`0021_local_identity` 在保留 `keycloak_subject`、本地租户类型、成员 `role_id` 和业务主键的前提下，删除 IAM 投影标识、同步时间、事件账本和迁移检查点。历史公共空间仍是一个受保护企业租户，业务表及其 `tenant_id` 不移动。

Keycloak 镜像暂时保留 `taiji-legacy-password-provider`，只用于验证尚未首次登录的历史 Werkzeug 密码摘要并促使 Keycloak 重新哈希。完成全部历史账号密码升级后可单独删除该提供器。

## 不变量

1. Keycloak 不创建或修改太极租户和成员关系。
2. OIDC token 不承载太极租户、成员角色或业务权限。
3. 太极请求不调用远程租户管理 API，也不依赖事件投影获得授权。
4. Keycloak、PostgreSQL 和 Redis 不直接暴露公网端口。
5. 外部域名变化时同时更新 `TAIJI_PUBLIC_URL`、`TAIJI_PUBLIC_URLS`、`IAM_PUBLIC_URL=<TAIJI_PUBLIC_URL>/iam` 和 Keycloak client redirect URI。
