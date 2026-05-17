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
| 配置管理 | python-dotenv | .env 自动加载 |
| 日志 | Python logging | 统一格式，stdout 输出 |
| 前端框架 | Vue 3 + Vite | SPA |
| UI 库 | Element Plus | 中后台组件 |
| 状态管理 | Pinia | 登录状态 + 用户信息 |
| 路由 | Vue Router 4 | 导航守卫 |
| 部署 | Docker Compose | backend/worker/frontend/redis |
| 测试 | pytest + pytest-flask | API 测试覆盖 |

---

## 开发阶段

### 第一阶段：后端骨架（含日志 + Celery 预留）

**目标：** Flask 项目能启动，访问 `/api/health` 返回 `{"status": "ok"}`

**步骤：**

1. 创建后端目录结构
2. `.env.example` — 环境变量模板
3. `config.py` — 配置类，使用 python-dotenv 自动加载 `.env`，读取：
   - `FLASK_ENV`、`SECRET_KEY`、`DATABASE_URL`、`REDIS_URL`
   - `JWT_SECRET_KEY`、`JWT_ACCESS_TOKEN_EXPIRES`、`JWT_REFRESH_TOKEN_EXPIRES`
4. `app/utils/logger.py` — 统一日志模块
   - 格式：`%(asctime)s [%(levelname)s] %(name)s: %(message)s`
   - 输出到 stdout（Docker 兼容）
   - 提供 `get_logger(name)` 工厂函数
5. `app/utils/errors.py` — 统一错误响应格式
   - `{"code": xxx, "message": "..."}`
   - 404/405/500 全局错误处理器
6. `app/__init__.py` — `create_app()` 工厂函数：
   - 初始化 SQLAlchemy、Flask-Migrate、JWT、CORS
   - 预留 `celery_app.init_app(app)` 调用（Phase 4 生效）
   - 注册蓝图（auth、analyze，允许蓝图尚不存在时跳过）
   - 注册错误处理器
7. `celery_app.py` — Celery 空壳（为 Phase 4 预留结构）
   - `create_celery_app(app=None)` 工厂函数
   - 后续 Phase 4 填充 Redis 配置
8. `run.py` — 调用 `create_app()` 并启动
9. `requirements.txt` — 所有依赖清单
10. `.gitignore` — 排除 `.env`、`data/`、`__pycache__`、`.venv/`

**验证：** `python run.py` → `curl localhost:5000/api/health` → `{"status": "ok"}`

---

### 第一点五阶段：测试基础设施

**目标：** pytest 框架就绪，至少一个示例测试通过

**步骤：**

1. 创建 `tests/` 目录
2. 安装 pytest + pytest-flask
3. `tests/conftest.py` — 测试 fixtures
   - `app` fixture：用测试配置创建 Flask 应用
   - `client` fixture：测试 HTTP 客户端
   - 测试数据库使用内存 SQLite（`:memory:`）
4. `tests/test_health.py` — 示例测试
   - `test_health_check`：验证 `/api/health` 返回 200 + `{"status": "ok"}`
5. `Makefile` — 添加 `make test` 命令

**验证：** `make test` → 所有测试通过

---

### 第二阶段：数据库模型

**目标：** 定义 User 和 AnalyzeTask 表，能执行 migration

**步骤：**

1. `app/models/user.py` — User 模型
   - id, username(unique), email, password_hash, created_at, updated_at
2. `app/models/analyze_task.py` — AnalyzeTask 模型
   - id, user_id(FK), url, status(enum: pending/running/success/failed), title, summary, keywords(JSON), error_message, created_at, started_at, completed_at
3. `app/models/__init__.py` — 统一导出所有模型
4. 在 `create_app()` 中配置 Flask-Migrate
5. 执行 `flask db init` → `flask db migrate` → `flask db upgrade`

**验证：** `sqlite3` 查看数据库，两张表已创建

---

### 第三阶段：认证系统

**目标：** 用户能注册、登录、获取 JWT，后端鉴权机制就绪

**步骤：**

1. `app/api/auth.py` — 认证蓝图
   - `POST /api/auth/register` — 注册（username + email + password）
   - `POST /api/auth/login` — 登录，返回 access_token + refresh_token
   - `POST /api/auth/refresh` — 刷新 access token
   - `GET /api/auth/me` — 获取当前用户信息
2. `app/services/auth_service.py` — 认证业务逻辑
   - 密码哈希/校验（werkzeug.security）
   - 用户创建/查询
   - token 签发（flask-jwt-extended）
3. `app/utils/jwt.py` — JWT 工具
   - `@jwt_required()` 装饰器封装
   - JWT 错误处理器（token 过期、无效、缺失）
4. `config.py` — JWT 配置
   - JWT_SECRET_KEY（从环境变量读取）
   - JWT_ACCESS_TOKEN_EXPIRES = 30 分钟
   - JWT_REFRESH_TOKEN_EXPIRES = 7 天
5. `tests/test_auth.py` — 认证测试
   - 注册成功 / 重复注册报错
   - 登录成功拿到 token / 密码错误报错
   - 无 token 访问 `/api/auth/me` → 401
   - 有效 token 访问 → 返回用户信息

**验证：** `curl` 走通注册 → 登录 → 访问 `/me`，pytest 全绿

---

### 第三点五阶段：前端骨架 + 登录

**目标：** Vue 3 项目跑起来，axios 拦截器自动刷新 token，登录页可用

> 设计理由：axios 拦截器（自动附带 token、自动刷新）是前端最核心的基础设施，应该尽早搭好、尽早验证。分析页面和历史列表留到 Phase 5。

**步骤：**

1. `npm create vite@latest frontend -- --template vue` 创建项目
2. 安装依赖：element-plus、pinia、vue-router、axios
3. `vite.config.js` — 配置开发代理 `/api` → `http://localhost:5000`
4. `src/api/request.js` — axios 实例（核心）
   - 请求拦截器：自动附加 `Authorization: Bearer <access_token>`
   - 响应拦截器：检测 401 → 自动用 refresh_token 换新 token → 重试原请求
   - 刷新失败 → 清除登录状态 → 跳转 `/login`
5. `src/api/auth.js` — 认证 API 封装
6. `src/stores/auth.js` — Pinia store
   - `state`: user, accessToken, refreshToken
   - `actions`: login(), register(), logout(), refreshToken(), fetchUser()
   - `persist`: token 存入 localStorage
7. `src/router/index.js` — 路由 + 导航守卫
   - 未登录 → `/login`
   - 已登录 → `/`（暂为占位页面，Phase 5 更新）
8. `src/views/Login.vue` — 登录页（Element Plus 表单）
9. `src/views/Register.vue` — 注册页
10. `src/App.vue` — 根布局框架（Element Plus Container）
11. `src/main.js` — 注册 Element Plus、Pinia、Router

**验证：** 前端启动 → 注册 → 登录成功 → 自动跳转到首页（占位页）

---

### 第四阶段：分析任务系统

**目标：** 提交 URL → Celery 异步抓取 → 返回分析结果，含完整容错

**步骤：**

1. `celery_app.py` — 填充 Celery 配置（Phase 1 空壳补全）
   - `create_celery_app(app=None)` 初始化 Celery
   - Redis broker + backend 配置
   - 序列化方式：json
   - Worker 启动时绑定 Flask app context
2. 在 `create_app()` 中调用 `celery_app.init_app(app)`
3. `app/api/analyze.py` — 分析蓝图
   - `POST /api/analyze/` — 提交 URL，返回 task_id
   - `GET /api/analyze/<task_id>` — 查询任务状态+结果
   - `GET /api/analyze/` — 分页查询历史任务
4. `app/services/analyze_service.py` — 分析业务逻辑
   - 创建任务记录（status=pending）
   - 查询任务状态
   - 分页查询历史（按用户 + 时间倒序）
5. `app/tasks/analyze_task.py` — Celery 任务（含完整容错）
   - `analyze_url(task_id)` 异步任务
   - `with app.app_context():` 包裹所有数据库操作
   - 更新 status 为 running + started_at
   - **容错机制：**
     - `requests.get(url, timeout=10)` — 超时 10 秒，异常捕获
     - `try/except requests.Timeout` → status=failed, error="请求超时"
     - `try/except requests.ConnectionError` → status=failed, error="无法连接"
     - BeautifulSoup 解析异常 → status=failed, error="网页解析失败"
     - 所有未预期异常 → status=failed, error_message=str(e)
   - 成功：提取 title、meta description、正文前 200 字 → status=success
   - 全流程 `logger.info()` 记录关键步骤
6. `tests/test_analyze.py` — 分析任务测试
   - 提交 URL 返回 task_id
   - 未登录提交 → 401

**验证：** POST 提交一个真实 URL → 拿 task_id → 轮询 GET → 拿到 title + summary

---

### 第五阶段：前端分析页面

**目标：** 主页能提交分析、查看结果、浏览历史

**步骤：**

1. `src/api/analyze.js` — 分析 API 封装
2. `src/stores/analyze.js` — Pinia store（可选，分析页用组件本地状态也行）
3. `src/views/Dashboard.vue` — 主页
   - URL 输入框 + 提交按钮
   - 提交后轮询任务状态（每 2 秒，最多 30 次）
   - 任务完成 → 展示结果卡片
   - 任务失败 → 展示错误信息
4. `src/views/TaskHistory.vue` — 历史任务列表
   - Element Plus Table 展示（URL、状态、时间、结果摘要）
   - 状态用 Tag 组件区分颜色（pending 灰、running 蓝、success 绿、failed 红）
   - 分页
5. `src/components/TaskResultCard.vue` — 分析结果卡片
   - 标题、摘要、关键词标签
   - 成功/失败两种形态
6. 更新 `src/router/index.js` — 添加 `/history` 路由

**验证：** 登录 → 提交 URL → 看到分析结果卡片 → 点击历史 → 看到任务列表

---

### 第六阶段：Docker 部署

**目标：** `docker compose up` 一键启动全部服务，数据持久化，健康检查

**步骤：**

1. `docker/Dockerfile.backend`
   - Python 3.11 slim 镜像
   - pip install -r requirements.txt
   - gunicorn 启动：`gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"`
2. `docker/Dockerfile.frontend`
   - Node 镜像 → npm ci → npm run build
   - Nginx 托管构建产物 + 反向代理 `/api` 到 backend
3. `docker/Dockerfile.worker`
   - 同 backend 镜像
   - CMD：`celery -A celery_app worker -l info`
4. `docker-compose.yml` — 编排 4 个服务

   | 服务 | 端口 | 关键配置 |
   |------|------|----------|
   | redis | 6379 (内部) | healthcheck: redis-cli ping |
   | backend | 5000 | depends_on redis (condition: healthy), volume: `./data:/app/data` |
   | worker | - | depends_on redis (condition: healthy), 同 data volume |
   | frontend | 80 | depends_on backend |

5. **Volume 持久化：** `docker-compose.yml` 内定义 `./data:/app/data`，SQLite 数据库文件存放在 `/app/data/taiji.db`
6. **环境变量注入：** `SECRET_KEY`、`JWT_SECRET_KEY` 通过 compose `environment:` 注入，生产环境使用强随机密钥
7. `Makefile` — 快捷命令
   - `make dev` — 开发模式（Flask + Celery worker + Vite 同时启动）
   - `make build` — 构建 Docker 镜像
   - `make up` — docker compose up -d
   - `make down` — docker compose down
   - `make test` — pytest

**验证：** `docker compose up` → 浏览器访问 `localhost` → 注册 → 登录 → 分析 → 完整流程走通

---

### 第七阶段：文档

**目标：** 新用户看 README 就能跑起来

1. `README.md` — 项目介绍 + 快速开始 + 目录结构说明 + 技术栈 + FAQ
2. 补充各模块内关键注释（特别是容错处理、JWT 刷新、Celery 上下文等容易踩坑的地方）

---

## 关键防坑措施

| 坑 | 措施 |
|----|------|
| Celery Worker 拿不到 Flask 上下文 | `create_celery_app()` + `with app.app_context()` |
| Celery 任务异常静默失败 | 全任务 `try/except` + error_message 写入数据库 + logger 记录 |
| 数据库 Schema 不同步 | Flask-Migrate (Alembic) |
| 前端跨域 | flask-cors(dev) + Vite proxy + Nginx(prod) |
| Token 过期用户无感知 | 前端 axios 拦截器自动刷新 |
| 密码硬编码 | .env + config.py + python-dotenv 自动加载 |
| 生产数据库默认 | 开发用 SQLite，生产通过 DATABASE_URL 切换到 PostgreSQL |
| Docker 容器重启丢数据 | `docker-compose.yml` volume 挂载 `./data:/app/data` |
| Redis 未就绪 backend 就启动 | docker-compose `depends_on` + Redis `healthcheck` |
| 缺乏测试保护 | pytest + pytest-flask，每个 Phase 都有对应测试 |
| 日志无处可查 | 统一日志模块，stdout 输出，Docker `docker logs` 直接查看 |

---

## 分支策略

- `main` — 稳定版本
- `dev` — 开发分支
- 每个阶段完成后合并回 `main`