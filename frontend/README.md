# Taiji Frontend

太极前端是 Vue 3 单页应用，使用 Vite、TypeScript、Pinia、Vue Router、Tailwind CSS、
Reka UI、Lucide 和 ECharts。生产构建由 Nginx 提供，并将 `/api/` 转发到 Flask、
将 `/iam/` 转发到内置 Keycloak。

## 本地开发

```bash
npm ci
npm run dev
```

Vite 默认监听 `http://localhost:5173`，并把 `/api` 代理到
`http://localhost:5000`。OIDC 完整登录依赖同源的 `/iam/`，因此认证流程和部署联调优先使用
仓库根目录的 `make docker-up`，统一入口默认为 `http://localhost:28080`。

## 校验

```bash
npm run type-check
npm run build
npm run preview
```

## 目录

- `src/api/`：Axios 接口与共享类型；`request.ts` 负责 Cookie 会话、CSRF 和 401 处理。
- `src/stores/auth.ts`：当前用户、租户列表、权限和租户切换。
- `src/router/index.js`：Hash 路由和认证、权限、平台管理员、企业租户守卫。
- `src/views/`：业务页面。
- `src/components/`：业务组件；`src/components/ui/` 为通用控件。
- `src/assets/theme.css`：全局语义颜色、间距和深色模式变量。
- `src/i18n/`：中英文文案。

浏览器不保存 OIDC access token。登录后端使用 Redis 服务端会话和 HttpOnly Cookie；
`GET /api/v1/auth/me` 返回的 CSRF token 由共享 Axios 实例附加到写请求。
