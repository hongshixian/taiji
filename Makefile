# 太极 (Taiji) Makefile

.PHONY: dev test build up down clean

# 开发模式 — 同时启动 Flask + Vite
dev:
	@echo "=== 启动 Flask 后端 ==="
	cd backend && python run.py &
	@sleep 2
	@echo "=== 启动 Vite 前端 ==="
	cd frontend && npm run dev

# 运行测试
test:
	cd backend && python -m pytest tests/ -v

# 构建 Docker 镜像
build:
	docker compose build

# 启动 Docker 服务
up:
	docker compose up -d

# 停止 Docker 服务
down:
	docker compose down

# 清理临时文件
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf backend/data/ *.db