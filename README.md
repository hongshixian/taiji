# ☯ 太极 (Taiji)

> Flask 3 + Vue 3 + Celery + Redis 全栈项目脚手架

太极是一个**即开即用的项目启动骨架**，内置用户认证、异步任务队列和示例业务（网页内容分析）。Clone 下来就能跑，零改动见完整链路。

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Flask 3 + SQLAlchemy + Flask-Migrate |
| 鉴权 | JWT (access 30min / refresh 7天) |
| 异步 | Celery + Redis |
| 前端 | Vue 3 + Vite + Element Plus + Pinia |
| 部署 | Docker Compose 一键启动 |

---

## 快速开始

### Docker 方式（推荐）

```bash
git clone https://github.com/hongshixian/taiji.git
cd taiji
docker compose up -d
```

浏览器打开 `http://localhost`，注册账号即可使用。

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

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|:---:|
| POST | `/api/auth/register` | 注册 | — |
| POST | `/api/auth/login` | 登录 | — |
| POST | `/api/auth/refresh` | 刷新 token | refresh |
| GET  | `/api/auth/me` | 当前用户 | ✓ |
| POST | `/api/analyze/` | 提交分析 | ✓ |
| GET  | `/api/analyze/<id>` | 查询任务 | ✓ |
| GET  | `/api/analyze/` | 历史列表 | ✓ |
| GET  | `/api/health` | 健康检查 | — |

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