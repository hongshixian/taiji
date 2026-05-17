# 太极 (Taiji) 分步实现方案

> Flask 3.x + Vue 3 + Celery + Redis 项目脚手架
> 示例任务：网页内容分析

---

## 技术栈总览

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端框架 | Flask 3.x | 蓝图组织接口 |
| API 序列化 | marshmallow | 请求校验 + 响应序列化 |
| 数据库 ORM | SQLAlchemy + Flask-Migrate | 用户表 + 分析任务表 |
| 鉴权 | flask-jwt-extended | access 30min / refresh 7天 |
| 异步任务 | Celery + Redis | broker + backend |
| 前端框架 | Vue 3 + Vite | SPA |
| UI 库 | Element Plus | 中后台组件 |
| 状态管理 | Pinia | 登录状态 + 用户信息 |
| 路由 | Vue Router 4 | 导航守卫 |
| 部署 | Docker Compose | backend/worker/frontend/redis |

---

## 开发阶段

### 第一阶段：后端骨架

**目标：** Flask 项目能启动，访问 `/api/health` 返回 `{"status": "ok"}`

**步骤：**

1. 创建后端目录结构
2. `config.py` — 配置类，从环境变量读取（FLASK_ENV、SECRET_KEY、DATABASE_URL、REDIS_URL）
3. `app/__init__.py` — `create_app()` 工厂函数：
   - 初始化 SQLAlchemy、Flask-Migrate、JWT、CORS
   - 注册蓝图（auth、analyze）
   - 注册错误处理器
4. `app/utils/errors.py` — 统一错误响应格式 `{"code": xxx, "message": "..."}`
5. `run.py` — 调用 `create_app()` 并启动
6. `requirements.txt` — 所有依赖清单
7. `.env.example` — 环境变量模板

**验证：** `python run.py` → `curl localhost:5000/api/health` → `{"status": "ok"}`

---

### 第二阶段：数据库模型

**目标：** 定义 User 和 AnalyzeTask 表，能执行 migration

**步骤：**

1. `app/models/user.py` — User 模型
   - id, username(unique), email, password_hash, created_at, updated_at
2. `app/models/analyze_task.py` — AnalyzeTask 模型
   - id, user_id(FK), url, status(enum), title, summary, keywords(JSON), error_message, created_at, started_at, completed_at
3. `app/models/__init__.py` — 统一导出所有模型
4. 在 `create_app()` 中配置 Flask-Migrate
5. 执行 `flask db init` → `flask db migrate` → `flask db upgrade`

**验证：** `sqlite3` 查看数据库，两张表已创建

---

### 第三阶段：认证系统

**目标：** 用户能注册、登录、获取 JWT，前端 axios 自动刷新 token

**步骤：**

1. `app/api/auth.py` — 认证蓝图
   - `POST /api/auth/register` — 注册（username + email + password）
   - `POST /api/auth/login` — 登录，返回 access_token + refresh_token
   - `POST /api/auth/refresh` — 刷新 access token
   - `GET /api/auth/me` — 获取当前用户信息
2. `app/services/auth_service.py` — 认证业务逻辑
   - 密码哈希/校验（werkzeug.security）
   - token 签发（flask-jwt-extended）
3. `app/utils/jwt.py` — JWT 工具
   - `@jwt_required()` 装饰器封装
   - 错误处理器（token 过期、无效）
4. `config.py` — JWT 配置
   - JWT_SECRET_KEY
   - JWT_ACCESS_TOKEN_EXPIRES = 30 分钟
   - JWT_REFRESH_TOKEN_EXPIRES = 7 天

**验证：** 注册 → 登录拿到 token → 用 token 访问 `/api/auth/me` → 返回用户信息

---

### 第四阶段：分析任务系统

**目标：** 提交 URL → Celery 异步抓取 → 返回分析结果

**步骤：**

1. `app/api/analyze.py` — 分析蓝图
   - `POST /api/analyze/` — 提交 URL，返回 task_id
   - `GET /api/analyze/<task_id>` — 查询任务状态+结果
   - `GET /api/analyze/` — 分页查询历史任务
2. `app/services/analyze_service.py` — 分析业务逻辑
   - 创建任务记录
   - 查询任务状态
3. `app/tasks/analyze_task.py` — Celery 任务
   - `analyze_url(task_id)` 异步任务
   - 用 requests 抓取网页
   - 用 BeautifulSoup 提取 title、meta description、正文摘要
   - 更新 AnalyzeTask 记录
4. `celery_app.py` — Celery 工厂
   - `create_celery_app()` 初始化 Celery，绑定 Flask app context
   - 配置 Redis broker + backend
5. 在 `create_app()` 中调用 `celery_app.init_app(app)`

**验证：** POST 提交一个 URL → 拿 task_id → 轮询 GET → 拿到分析结果

---

### 第五阶段：前端开发

**目标：** Vue 3 前端，含登录注册、分析页面、历史列表

**步骤：**

1. `vite create` 创建 Vue 3 项目 → 安装 Element Plus、Pinia、Vue Router、axios
2. `vite.config.js` — 配置开发代理 `/api` → `http://localhost:5000`
3. `src/api/request.js` — axios 实例
   - 请求拦截器：自动附加 `Authorization: Bearer <token>`
   - 响应拦截器：401 时自动用 refresh_token 换取新 token，重试原请求
4. `src/api/auth.js` — 登录/注册/刷新/获取用户 API
5. `src/api/analyze.js` — 提交分析/查询结果/历史列表 API
6. `src/stores/auth.js` — Pinia store
   - `login()` / `register()` / `logout()` / `refreshToken()`
7. `src/router/index.js` — 路由配置 + 导航守卫（未登录 → `/login`）
8. `src/views/Login.vue` — 登录页（Element Plus 表单）
9. `src/views/Register.vue` — 注册页
10. `src/views/Dashboard.vue` — 主页
    - 输入 URL → 提交分析 → 轮询结果 → 展示结果卡片
11. `src/views/TaskHistory.vue` — 历史任务列表
12. `src/components/TaskResultCard.vue` — 分析结果卡片（标题、摘要、关键词）
13. `src/App.vue` — 根布局（侧边栏 + 顶部导航）

**验证：** 前端启动 → 注册 → 登录 → 提交 URL → 看到分析结果 → 查看历史

---

### 第六阶段：Docker 部署

**目标：** `docker compose up` 一键启动全部服务

**步骤：**

1. `docker/Dockerfile.backend` — Python 镜像 → pip install → gunicorn 启动
2. `docker/Dockerfile.frontend` — Node 镜像 → npm build → Nginx 托管
3. `docker/Dockerfile.worker` — 同 backend，但 CMD 是 celery worker
4. `docker-compose.yml` — 编排 4 个服务
   - redis:6379
   - backend:5000
   - worker (内部)
   - frontend:80
   - 环境变量注入（SECRET_KEY、DATABASE_URL 等）
5. `Makefile` — 快捷命令
   - `make dev` — 开发模式启动
   - `make build` — 构建镜像
   - `make up` — docker compose up

**验证：** `docker compose up` → 浏览器访问 `localhost` → 完整流程走通

---

### 第七阶段：文档

**目标：** 新用户看 README 就能跑起来

1. `README.md` — 项目介绍 + 快速开始 + 目录结构说明 + 技术栈
2. 补充各模块内注释

---

## 关键防坑措施

| 坑 | 措施 |
|----|------|
| Celery Worker 拿不到 Flask 上下文 | `create_celery_app()` + `with app.app_context()` |
| 数据库 Schema 不同步 | Flask-Migrate (Alembic) |
| 前端跨域 | flask-cors(dev) + Vite proxy + Nginx(prod) |
| Token 过期用户无感知 | 前端 axios 拦截器自动刷新 |
| 密码硬编码 | .env + config.py 环境变量注入 |
| 生产数据库默认 | 开发用 SQLite，生产通过 DATABASE_URL 切换到 PostgreSQL |

---

## 分支策略

- `main` — 稳定版本
- `dev` — 开发分支
- 每个阶段完成后合并回 `main`