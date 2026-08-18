# 太极 (Taiji) Makefile

.PHONY: dev test build up down docker-build docker-up docker-down clean iam-build iam-test iam-up iam-down iam-smoke iam-integration-test iam-migration-integration-test iam-bootstrap-password iam-reconcile k8s-validate k8s-sync-images k8s-build-push k8s-secret k8s-deploy k8s-status k8s-delete

DOCKER_DEPLOY_DIR := deploy/taiji-docker
COMPOSE_OVERRIDE := $(wildcard $(DOCKER_DEPLOY_DIR)/docker-compose.override.yml)
COMPOSE := docker compose --env-file $(DOCKER_DEPLOY_DIR)/.env \
	-f $(DOCKER_DEPLOY_DIR)/docker-compose.yml \
	$(if $(COMPOSE_OVERRIDE),-f $(COMPOSE_OVERRIDE),)
K8S_DEPLOY_DIR := deploy/taiji-k8s
KUBE_NAMESPACE ?= lihao
HARBOR_REGISTRY ?= harbor.aixiongan.org.cn:9443/lihao
IMAGE_TAG ?= b059d56

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
	$(COMPOSE) build

docker-build: build

# 启动 Docker 服务
up:
	$(COMPOSE) up -d

docker-up: up

# 停止 Docker 服务
down:
	$(COMPOSE) down

docker-down: down

# 构建并运行 Keycloak 扩展测试
iam-build:
	$(COMPOSE) build keycloak

iam-test:
	docker run --rm -v taiji_maven_cache:/root/.m2 -v "$(CURDIR)/iam/keycloak-extension:/build" -w /build maven:3.9.11-eclipse-temurin-21 mvn --batch-mode test

iam-up:
	$(COMPOSE) up -d postgres keycloak-db-init nats keycloak iam-proxy iam-bootstrap

iam-down:
	$(COMPOSE) stop iam-proxy keycloak nats

iam-smoke:
	./scripts/iam-smoke.sh

iam-integration-test:
	./scripts/iam-integration-test.sh

iam-migration-integration-test:
	./scripts/iam-migration-integration-test.sh

iam-bootstrap-password:
	$(COMPOSE) logs --no-log-prefix iam-bootstrap

iam-reconcile:
	$(COMPOSE) run --rm --no-deps iam-projector python iam_projector.py --reconcile-only

k8s-validate:
	@unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY; \
	kubectl kustomize $(K8S_DEPLOY_DIR) >/dev/null; \
	kubectl apply --dry-run=client -k $(K8S_DEPLOY_DIR) >/dev/null; \
	kubectl apply --dry-run=server -k $(K8S_DEPLOY_DIR) >/dev/null

k8s-sync-images:
	@set -e; \
	for image in postgres:16-alpine redis:7-alpine nats:2.11.8-alpine nginx:alpine; do \
		docker image inspect "$$image" >/dev/null 2>&1 || docker pull "$$image"; \
		docker tag "$$image" "$(HARBOR_REGISTRY)/$$image"; \
		docker push "$(HARBOR_REGISTRY)/$$image"; \
	done

k8s-build-push:
	docker build -f $(DOCKER_DEPLOY_DIR)/Dockerfile.backend -t $(HARBOR_REGISTRY)/taiji-backend:$(IMAGE_TAG) .
	docker build -f $(DOCKER_DEPLOY_DIR)/Dockerfile.worker -t $(HARBOR_REGISTRY)/taiji-worker:$(IMAGE_TAG) .
	docker build -f $(DOCKER_DEPLOY_DIR)/Dockerfile.frontend -t $(HARBOR_REGISTRY)/taiji-frontend:$(IMAGE_TAG) .
	docker build -f $(DOCKER_DEPLOY_DIR)/Dockerfile.keycloak -t $(HARBOR_REGISTRY)/taiji-keycloak:$(IMAGE_TAG) .
	docker push $(HARBOR_REGISTRY)/taiji-backend:$(IMAGE_TAG)
	docker push $(HARBOR_REGISTRY)/taiji-worker:$(IMAGE_TAG)
	docker push $(HARBOR_REGISTRY)/taiji-frontend:$(IMAGE_TAG)
	docker push $(HARBOR_REGISTRY)/taiji-keycloak:$(IMAGE_TAG)

k8s-secret:
	KUBE_NAMESPACE=$(KUBE_NAMESPACE) ./scripts/k8s-create-secret.sh

k8s-deploy: k8s-secret
	@unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY; \
	kubectl delete job taiji-iam-bootstrap -n $(KUBE_NAMESPACE) --ignore-not-found; \
	kubectl apply -k $(K8S_DEPLOY_DIR)

k8s-status:
	@unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY; \
	kubectl get pods,services,persistentvolumeclaims,jobs -n $(KUBE_NAMESPACE) \
		-l app.kubernetes.io/part-of=taiji -o wide

k8s-delete:
	@unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY; \
	kubectl delete -k $(K8S_DEPLOY_DIR) --ignore-not-found

# 清理临时文件
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf backend/data/ *.db
