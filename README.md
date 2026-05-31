# ☯ 太极 (Taiji)

> Flask 3 + Vue 3 + Celery + Redis 全栈项目脚手架

太极是一个**即开即用的项目启动骨架**，内置用户认证、异步任务队列和示例业务（网页内容分析）。Clone 下来就能跑，零改动见完整链路。

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Flask 3 + SQLAlchemy + Flask-Migrate |
| 鉴权 | JWT (access 30min / refresh 7天) + Redis 黑名单 |
| 权限 | RBAC（角色-权限分离，运行时可配） |
| 多租户 | 共享 schema + 全局 query 拦截器（数据自动隔离） |
| 异步 | Celery + Redis |
| 前端 | Vue 3 + Vite + Element Plus + Pinia |
| 部署 | Docker Compose 一键启动 |

---

## 快速开始

### Docker 方式（推荐）

```bash
git clone https://github.com/hongshixian/taiji.git
cd taiji
cp .env.example .env       # 推荐：编辑 .env 设置 ADMIN_PASSWORD 与密钥
docker compose up -d
```

浏览器打开 `http://localhost`，注册账号即可使用。

#### 首次部署：管理员账号

- **若设置了 `ADMIN_PASSWORD`**（推荐）：使用 `ADMIN_USERNAME` / `ADMIN_PASSWORD` 登录
- **未设置 `ADMIN_PASSWORD`**：启动时会随机生成密码并打印到日志，**请立即查看并保存**：

  ```bash
  docker compose logs backend | grep -A 5 "首次部署"
  ```

  登录后请到「用户管理」改成你能记住的强密码。该密码仅在首次启动（DB 无 admin 时）生成一次，之后不再打印。

### 本地开发

```bash
# 1. 后端
cd backend
cp .env.example .env    # 编辑数据库和密钥
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
├── docker/               # Dockerfile × 3
├── docker-compose.yml    # 四服务编排
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

> 所有业务接口都在 `/api/v1/` 之下；`/api/health` 跨版本稳定。

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|:---:|
| POST | `/api/v1/auth/register` | 注册（默认进 guest 租户）| — |
| POST | `/api/v1/auth/login` | 登录 | — |
| POST | `/api/v1/auth/refresh` | 刷新 token | refresh |
| POST | `/api/v1/auth/logout` | 退出（撤销当前 token）| ✓ |
| PUT  | `/api/v1/auth/password` | 修改密码（踢出所有会话）| ✓ |
| GET  | `/api/v1/auth/me` | 当前用户（含 perms）| ✓ |
| POST | `/api/v1/analyze/` | 提交分析 | task:create |
| GET  | `/api/v1/analyze/<id>` | 查询任务 | task:read |
| GET  | `/api/v1/analyze/` | 历史列表 | task:read |
| POST | `/api/v1/analyze/<id>/retry` | 重试失败任务 | task:create |
| GET/POST/PUT/DELETE | `/api/v1/admin/users[/<id>]` | 用户 CRUD | user:read/write/delete |
| GET/POST/PUT/DELETE | `/api/v1/admin/roles[/<id>]` | 角色 CRUD | role:read/write/delete |
| GET  | `/api/v1/admin/roles/permissions` | 所有权限码列表 | role:read |
| GET/POST/PUT/DELETE | `/api/v1/superadmin/tenants[/<id>]` | 租户 CRUD（仅 superuser）| is_superuser |
| GET  | `/api/health` | 健康检查 | — |

### 响应格式

所有 API 统一返回：

```json
{ "code": 0, "message": "ok", "data": { ... } }
```

- `code = 0` 成功；非 0 为业务错误码（详见 `backend/app/utils/errors.py::ErrorCode`）
- 错误码分段：`1xxxx` 用户/认证、`11xxx` 多租户、`2xxxx` 任务、`3xxxx` 鉴权、`9xxxx` 系统级

### 权限体系 (RBAC)

| 角色 | 权限 |
|------|------|
| `admin` | 全部权限（user:*/role:*/task:*/system:*）|
| `user` | task:read, task:create |
| `guest` | task:read |

- 系统角色 (is_system=true) 不可删除；admin 可在「角色管理」页新增自定义角色
- 角色挂在租户成员身份 (`tenant_memberships.role_id`) 上，同一用户在不同租户可拥有不同角色
- 改密 / 改角色 / 禁用账户或成员身份会立即撤销该用户所有 JWT（用户级吊销 + Redis 黑名单）
- 平台超级管理员通过 `is_superuser` 管理租户和系统设置；租户管理员通过当前租户角色权限管理成员与角色

### 多租户

- 数据库层面共享 schema，每张业务表带 `tenant_id`，全局 query 拦截器自动按当前 tenant 过滤
- `users` 是全局唯一登录主体，`username` / `email` 全局唯一
- 用户通过 `tenant_memberships` 归属多个租户；JWT 当前 `tenant_id` 表示当前操作租户
- 登录只校验全局账号密码并进入默认可用租户，其他租户通过右上角租户切换器切换
- 系统种子租户：`default`（现有数据）+ `guest`（公开注册落地）
- **超级管理员** (is_superuser=true)：可跨租户管理，通过 `/api/v1/superadmin/tenants` 增删改租户
- **系统设置**：超级管理员可通过 `/api/v1/superadmin/settings` 配置平台级选项，例如新注册用户默认所属租户
- **超级管理员列表**：超级管理员可添加 / 移除其他用户的平台超级管理员权限
- **租户成员管理**：超级管理员可在租户管理页向任意租户添加 / 移除成员
- 普通用户可通过 `/api/v1/auth/switch-tenant` 切换到自己拥有成员身份的租户

---

## 运行测试

```bash
cd backend
python -m pytest tests/ -v
```

21 个测试覆盖：健康检查、注册登录、JWT 鉴权、Token 刷新、分析任务 API。

---

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SECRET_KEY` | Flask 密钥 | `dev-secret-change-me` |
| `DATABASE_URL` | 数据库地址 | `sqlite:///../data/taiji.db` |
| `REDIS_URL` | Redis 地址 | `redis://localhost:6379/0` |
| `JWT_SECRET_KEY` | JWT 签名密钥 | — |

---

## License

MIT © hongshixian
