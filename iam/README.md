# Taiji 登录内核

本目录保存太极专用的 Keycloak Realm、登录主题、账号中心和历史密码校验 provider。Keycloak 是太极内部组件，不作为独立 IAM 产品发布，也不保存业务租户、成员关系或业务权限。

## 目录职责

- `realm/`：`fangcun` Realm 与 `taiji-web` OIDC 客户端基线。
- `themes/taiji/login/`：登录、注册、找回密码和必做动作页面。
- `account-console/`：基于官方 Keycloak Account UI 的账号与密码管理界面。
- `keycloak-extension/`：只保留历史 Werkzeug 密码哈希兼容 provider。
- `config/user-profile.json`：登录用户资料字段约束。

用户、个人空间、企业租户、成员关系、平台管理员、租户管理员和业务权限均以 Taiji PostgreSQL 数据为准。Keycloak 的 `platform_admin` realm role 只在用户第一次进入 Taiji 时引导本地超级管理员，之后不会覆盖本地授权。

## 版本基线

- Keycloak 与 Account UI：26.7.0
- Java：21
- Maven：3.9.11
- Node.js：20

版本由 `deploy/taiji-docker/Dockerfile.keycloak`、扩展 `pom.xml` 和 `account-console/package.json` 固定。升级时必须同步服务端、Java provider 和 Account UI，并重新执行镜像构建、后端测试和浏览器冒烟验证。

## 构建与启动

根据 `deploy/taiji-docker/.env.example` 创建本地 `.env`，再构建并启动完整太极平台：

```bash
make build
make up
make iam-smoke
```

默认统一入口：

- 太极平台：`http://localhost:28080/`
- 登录与账号中心：`http://localhost:28080/iam/`
- OIDC Discovery：`http://localhost:28080/iam/realms/fangcun/.well-known/openid-configuration`
- 后端 API：`http://localhost:28080/api/`

只有前端 Nginx 暴露宿主机端口。Keycloak、后端、PostgreSQL 和 Redis 只通过 Compose 内部网络访问。

当前本机 Docker 开发域名是 `https://taiji.lihao.fun`，Kubernetes 生产域名是
`https://evaluation.fangcunleap.com`；两者都把 Keycloak 放在各自主域名的 `/iam/`，且数据独立。

## 验证

```bash
make iam-test
cd iam/account-console && npm ci && npm run build
```

完整 Keycloak 镜像构建会执行 Maven 测试，将账号中心与历史密码 provider 打入镜像，并在构建期执行 `kc.sh build`。运行时使用 `start --optimized`，避免重复增强。

真实 OIDC 流程可使用 `scripts/oidc-browser-smoke.py`、`scripts/oidc-registration-smoke.py` 和 `scripts/oidc-platform-smoke.py` 验证。

## 生产约束

- 禁止使用示例密码、Client Secret 或 Flask Secret。
- 公网只暴露太极统一入口，由 `/iam/` 路由转发到 Keycloak。
- Keycloak Admin Console 只允许运维网络访问。
- Keycloak 数据库与 Taiji 业务数据库使用独立逻辑数据库。
- 升级与历史数据处理见 `docs/operations/iam-migration.md`。
