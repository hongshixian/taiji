# ☯ 太极 (Taiji)

> Flask 3 + Vue 3 + Keycloak 的多租户评测平台

太极是一个多租户 AI 安全评测平台。Keycloak 作为平台内置登录内核，仅负责账号凭证和 OIDC 认证；用户业务记录、个人空间、企业租户、成员关系和权限均以太极数据库为唯一权威。

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Flask 3 + SQLAlchemy + Flask-Migrate |
| 鉴权 | Keycloak OIDC + PKCE + Redis 服务端会话 + CSRF |
| 权限 | 太极本地租户成员关系 + RBAC 权限矩阵 |
| 多租户 | 共享 schema + 全局 query 拦截器（数据自动隔离） |
| 异步 | Celery + Redis |
| 前端 | Vue 3 + Vite + Element Plus + Pinia |
| 登录入口 | 同源 `/iam/`，不单独暴露 Keycloak 端口 |
| 部署 | Docker Compose / Kubernetes（PostgreSQL、Keycloak、Redis） |

---

## 快速开始

### Docker 方式（推荐）

```bash
git clone https://github.com/hongshixian/taiji.git
cd taiji
cp deploy/taiji-docker/.env.example deploy/taiji-docker/.env
# 编辑 deploy/taiji-docker/.env 中的生产 Secret 与公网 URL
make docker-up
```

浏览器打开 `http://localhost:28080`，注册账号即可使用。

#### 首次部署：平台管理员

- 登录引导任务仅在空 Realm 中创建用户名 `admin`，密码由安全随机源生成并标记为首次登录强制修改。
- 临时密码只由一次性 `iam-bootstrap` 任务输出一次：

  ```bash
  make iam-bootstrap-password
  ```

基础设施管理员 `KEYCLOAK_BOOTSTRAP_ADMIN_USERNAME` 与太极平台管理员不是同一账号，不能用于业务登录。

### Kubernetes 方式

Kubernetes 使用 Harbor 中的镜像和 Kustomize 清单，当前默认只创建集群内部的
`ClusterIP`，不会对公网暴露端口：

```bash
make k8s-validate
make k8s-sync-images
make k8s-build-push
make k8s-deploy
make k8s-status
```

完整的资源、存储和内部端口说明见
[`deploy/taiji-k8s/README.md`](deploy/taiji-k8s/README.md)。

### 本地开发

```bash
# 1. 后端
cd backend
cp ../deploy/taiji-docker/.env.example .env  # 编辑数据库和密钥
pip install -r requirements.txt
flask db upgrade
python run.py            # 启动于 :5000

# 2. Worker（新终端）
cd backend
celery -A celery_app worker -l info

# 3. 前端（新终端）
cd frontend
npm install
npm run dev              # 启动于 :5173
```

---

## 项目结构

```
taiji/
├── backend/
│   ├── app/
│   │   ├── api/          # 蓝图 — 接口层
│   │   ├── models/       # SQLAlchemy 模型
│   │   ├── services/     # 业务逻辑层
│   │   ├── tasks/        # Celery 异步任务
│   │   └── utils/        # 日志、错误处理、JWT 工具
│   ├── tests/            # pytest 测试
│   ├── config.py         # 环境变量配置
│   ├── celery_app.py     # Celery 实例
│   └── run.py            # Flask 启动入口
├── frontend/
│   └── src/
│       ├── api/          # axios 封装 + 拦截器
│       ├── router/       # 路由 + 导航守卫
│       ├── stores/       # Pinia 状态
│       └── views/        # 页面组件
├── deploy/
│   ├── taiji-docker/      # Compose、Dockerfile 与容器配置
│   └── taiji-k8s/         # Kubernetes Kustomize 部署清单
├── iam/                  # Keycloak Realm、Theme 与历史密码兼容提供器
├── Makefile              # Docker/Kubernetes 运维入口
└── README.md
```

---

## 示例任务：网页内容分析

1. 登录后输入任意 URL
2. 点击「开始分析」
3. Celery 异步抓取网页，提取标题、摘要、关键词
4. 结果实时展示，历史记录可查

---

## API 总览

> 所有业务接口都在 `/api/v1/` 之下；`/api/health` 和 `/api/ready` 跨版本稳定。

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|:---:|
| GET | `/api/v1/auth/register` | 跳转统一登录注册 | — |
| GET | `/api/v1/auth/login` | 发起 OIDC Authorization Code + PKCE | — |
| GET | `/api/v1/auth/callback` | OIDC 回调并建立服务端会话 | state/nonce |
| POST | `/api/v1/auth/logout` | 销毁本地会话并返回统一登录退出地址 | CSRF |
| GET | `/api/v1/auth/me` | 当前用户、租户、权限和 CSRF token | session |
| POST | `/api/v1/auth/switch-tenant` | 切换当前会话生效租户 | session + CSRF |
| GET  | `/api/v1/tasks/` | 所有任务列表 | task:read |
| GET  | `/api/v1/tasks/<id>/logs` | 任务执行日志 | task:read |
| POST | `/api/v1/tasks/webpage-analysis/` | 提交网页分析 | task:create |
| GET  | `/api/v1/tasks/webpage-analysis/<id>` | 查询网页分析任务 | task:read |
| GET  | `/api/v1/tasks/webpage-analysis/` | 网页分析历史列表 | task:read |
| POST | `/api/v1/tasks/webpage-analysis/<id>/retry` | 重试网页分析任务 | task:create |
| DELETE | `/api/v1/tasks/webpage-analysis/<id>` | 删除网页分析任务 | task:delete:any |
| POST | `/api/v1/tasks/csv-quality/` | 提交 CSV 数据质量检查 | task:create |
| GET  | `/api/v1/tasks/csv-quality/<id>` | 查询 CSV 检查任务 | task:read |
| GET  | `/api/v1/tasks/csv-quality/` | CSV 检查历史列表 | task:read |
| POST | `/api/v1/tasks/csv-quality/<id>/retry` | 重试 CSV 检查任务 | task:create |
| DELETE | `/api/v1/tasks/csv-quality/<id>` | 删除 CSV 检查任务 | task:delete:any |
| GET/POST/PUT/DELETE | `/api/v1/admin/users[/<id>]` | 企业租户成员管理（兼容路径） | member:* |
| GET/POST/PUT/DELETE | `/api/v1/superadmin/tenants[/<id>]` | 企业租户创建、修改和停用 | platform_admin |
| GET/POST/DELETE | `/api/v1/superadmin/superusers[/<id>]` | 平台管理员授权（兼容路径） | platform_admin |
| GET  | `/api/v1/audit-logs` | 审计日志查询 | system:audit |
| GET  | `/api/health` | 健康检查 | — |
| GET  | `/api/ready` | 数据库、Redis、登录内核就绪检查 | — |

### 响应格式

所有 API 统一返回：

```json
{ "code": 0, "message": "ok", "data": { ... } }
```

- `code = 0` 成功；非 0 为业务错误码（详见 `backend/app/utils/errors.py::ErrorCode`）
- 错误码分段：`1xxxx` 用户/认证、`11xxx` 多租户、`2xxxx` 任务、`3xxxx` 鉴权、`9xxxx` 系统级

### 权限体系

| 角色 | 权限 |
|------|------|
| `tenant_admin` | 成员管理、全部任务、模型配置、评测管理和审计 |
| `member` | 全部任务、模型配置和评测只读 |

- `tenant_admin` 与 `member` 都是太极本地成员身份，对应本地 `admin` / `user` 系统角色。
- Keycloak 令牌不包含租户或业务权限，不能修改太极授权状态。
- 平台超级管理员只管理租户和平台管理员；没有 membership 时不能读取租户业务数据。
- 租户、成员、角色或账号状态改变后，下一次请求会从本地数据库刷新服务端会话。
- 审计日志通过 `system:audit` 查看：超级管理员可跨租户查询，租户管理员只能查看当前租户日志

### 任务扩展架构

- 通用任务生命周期存放在 `tasks` 总表：租户、创建者、任务类型、状态、错误、时间字段
- 任务执行日志走 JSONL 文件：`TASK_LOG_ROOT/tasks/tenant_{tenant_id}/{task_type}/task_{task_id}.jsonl`
- `tasks.log_path` 只保存日志相对路径；日志明细不写数据库
- 不同业务使用独立详情表：`webpage_analysis_tasks`、`csv_quality_tasks`
- 后端业务逻辑按模块拆分：独立 schema、service、API 蓝图和 Celery task
- 新增第三类任务时，优先新增一张详情表和一套独立业务模块，不把业务字段塞进通用任务表

### 多租户

- 数据库层面共享 schema，每张业务表带 `tenant_id`，全局 query 拦截器自动按当前 tenant 过滤
- `users` 是全局唯一登录主体，`username` / `email` 全局唯一
- 用户通过 `tenant_memberships` 归属多个租户；当前 `tenant_id` 只保存在每个浏览器服务端会话中。
- 用户登录时无需选择租户，Header 下拉框读取太极数据库中的全部可用租户；一次会话只激活一个租户。
- 每个自行注册用户自动拥有一个受保护个人空间，并在其中拥有完整业务权限。
- 企业租户由平台管理员创建，租户管理员可直接加入已经完成首次登录的全局用户。
- 历史公共空间迁移为一个受保护企业租户，业务表主键和 `tenant_id` 不移动。

IAM 架构见 [docs/architecture/iam.md](docs/architecture/iam.md)，生产发布按 [docs/operations/iam-deployment.md](docs/operations/iam-deployment.md) 执行。

---

## 运行测试

```bash
cd backend
python -m pytest tests/ -v
```

56 个后端测试覆盖 OIDC BFF、CSRF、个人空间、本地租户切换、多租户隔离、固定权限、旧认证回滚路径和审计日志；Keycloak 历史密码兼容提供器另有 4 个 Maven 测试。

---

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SECRET_KEY` | Flask 密钥 | `dev-secret-change-me` |
| `DATABASE_URL` | 数据库地址 | `sqlite:///../data/taiji.db` |
| `REDIS_URL` | Redis 地址 | `redis://localhost:6379/0` |
| `AUTH_MODE` | 认证模式；生产为 `oidc` | `legacy` |
| `IAM_PUBLIC_URL` | 浏览器访问内置登录路由 | `http://localhost:28080/iam` |
| `IAM_INTERNAL_URL` | 后端访问 Keycloak 的地址 | 同 `IAM_PUBLIC_URL` |
| `TAIJI_PUBLIC_URL` | 浏览器访问太极的地址 | `http://localhost:28080` |
| `TAIJI_OIDC_CLIENT_SECRET` | OIDC Web Client Secret | 仅开发默认值 |
| `TASK_LOG_ROOT` | 任务日志根目录 | `../app_logs` |

---

## License

MIT © hongshixian
