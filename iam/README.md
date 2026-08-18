# Taiji IAM

本目录保存太极专用的 Keycloak 扩展、Realm 声明和主题。它随 `taiji` 仓库维护，与同级其他仓库无关。

## 版本基线

- Keycloak: 26.7.0
- Keycloak Account UI: 26.7.0
- Java: 21
- Maven: 3.9.11
- Node.js: 20
- NATS Server: 2.11.8

版本在 `deploy/taiji-docker/Dockerfile.keycloak`、`deploy/taiji-docker/docker-compose.yml`、扩展 `pom.xml` 和 `account-console/package.json` 中固定。升级 Keycloak 时必须同步服务端、Java 扩展和 Account UI 版本，并重新执行扩展测试和浏览器验证。

## 界面主题

- `themes/taiji/login` 覆盖 Keycloak 托管的登录、注册、找回密码、必做动作和状态页面。
- `account-console` 使用官方 `@keycloak/keycloak-account-ui` 页面组件，提供方寸品牌外壳、导航和响应式布局。
- `Dockerfile.keycloak` 在构建期将账号中心打包成 `fangcun-account-ui.jar`，与 Keycloak 同进程发布，不增加独立运行端口。
- `iam-bootstrap-admin.sh` 幂等设置 `loginTheme=taiji`、`accountTheme=fangcun-account` 和 Realm 语言配置。

账号中心前端可单独执行静态构建检查：

```bash
cd iam/account-console
npm ci
npm run build
```

## 本地启动

先根据 `deploy/taiji-docker/.env.example` 配置 `deploy/taiji-docker/.env`。模板中的 IAM 密码和 Client Secret 只允许用于开发环境。

```bash
make iam-build
make iam-up
make iam-smoke
```

默认地址：

- Keycloak: `http://localhost:8180`
- Realm: `fangcun`
- OIDC Discovery: `http://localhost:8180/realms/fangcun/.well-known/openid-configuration`
- 扩展健康检查: `http://localhost:8180/realms/fangcun/taiji-iam/health`

停止 IAM 组件：

```bash
make iam-down
```

`keycloak-db-init` 会在现有 PostgreSQL 实例中幂等创建独立的 `keycloak` 逻辑数据库。NATS JetStream 数据保存在 Docker 命名卷 `taiji_nats_data`。

## 扩展测试

宿主机不需要安装 Java 或 Maven：

```bash
make iam-test
```

Maven 依赖保存在 Docker 命名卷 `taiji_maven_cache`，重复测试不会重新下载全部依赖。完整 Keycloak 镜像构建还会执行相同的 `mvn verify`，随后运行 `kc.sh build` 验证 SPI 能被 Keycloak 发现。

## 旧数据迁移

迁移默认只做只读预检，一次性迁移端点在日常运行时保持关闭。执行顺序、安全要求、续跑和回滚步骤见 [`docs/operations/iam-migration.md`](../docs/operations/iam-migration.md)。

隔离测试环境可运行真实旧密码换密验证：

```bash
make iam-migration-integration-test
```

## 生产约束

- 禁止使用 `deploy/taiji-docker/.env.example` 中的任何默认密码或 Secret。
- 使用 `start` 和正式 HTTPS 域名，不使用 Compose 中的 `start-dev`。
- Keycloak Admin Console 只能从运维网络访问。
- NATS 使用持久化集群、独立账号和 TLS。
- Keycloak 升级必须先验证自定义 REST 和 Event Listener SPI 兼容性。
