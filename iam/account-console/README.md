# Fangcun Account Console

方寸 IAM 账号中心基于 Keycloak 官方 `@keycloak/keycloak-account-ui` 组件构建，服务端与前端版本固定为 26.7.0。自定义工程负责方寸品牌外壳、导航与响应式布局；个人资料、密码、会话、应用、组织和用户组功能继续使用 Keycloak 官方实现。

## 本地校验

```bash
npm ci
npm run build
```

生产构建由 `docker/Dockerfile.keycloak` 的 Maven 阶段打包为 Keycloak 主题 Provider JAR，不需要单独部署前端服务。
