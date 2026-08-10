# 太极 (Taiji) Makefile

.PHONY: dev test build up down clean iam-build iam-test iam-up iam-down iam-smoke iam-integration-test iam-migration-integration-test iam-bootstrap-password iam-reconcile

# 开发模式 — 同时启动 Flask + Vite
dev:
	@echo "=== 启动 Flask 后端 ==="
	cd backend && python run.py &
	@sleep 2
	@echo "=== 启动 Vite 前端 ==="
	cd frontend && npm run dev

# 运行测试
test:
	cd backend && /usr/bin/python3 -m pytest tests/ -v

# 构建 Docker 镜像
build:
	docker compose build

# 启动 Docker 服务
up:
	docker compose up -d

# 停止 Docker 服务
down:
	docker compose down

# 构建并运行 Keycloak 扩展测试
iam-build:
	docker compose build keycloak

iam-test:
	docker run --rm -v taiji_maven_cache:/root/.m2 -v "$(CURDIR)/iam/keycloak-extension:/build" -w /build maven:3.9.11-eclipse-temurin-21 mvn --batch-mode test

iam-up:
	docker compose up -d postgres keycloak-db-init nats keycloak iam-bootstrap

iam-down:
	docker compose stop keycloak nats

iam-smoke:
	./scripts/iam-smoke.sh

iam-integration-test:
	./scripts/iam-integration-test.sh

iam-migration-integration-test:
	./scripts/iam-migration-integration-test.sh

iam-bootstrap-password:
	docker compose logs --no-log-prefix iam-bootstrap

iam-reconcile:
	docker compose run --rm --no-deps iam-projector python iam_projector.py --reconcile-only

# 清理临时文件
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf backend/data/ *.db
