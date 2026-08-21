# CLAUDE.md

This file gives coding agents the current repository conventions. Read `README.md` and the
component-specific documentation before changing an architectural boundary.

## Project overview

Taiji is a multi-tenant AI evaluation platform built with Flask 3, Vue 3, Celery, Redis,
PostgreSQL and an embedded Keycloak 26.7 login kernel. Production authentication uses an
OIDC BFF: tokens stay in a Redis-backed server session and the browser holds only an HttpOnly
cookie. Keycloak authenticates users; Taiji PostgreSQL owns users' business records, personal
spaces, enterprise tenants, memberships, roles and permissions.

`AUTH_MODE=legacy` remains only as a rollback path. Do not design new features around browser
JWTs, Keycloak Organizations or a separate IAM platform.

## Common commands

```bash
# Full Docker development stack (repo root)
cp deploy/taiji-docker/.env.example deploy/taiji-docker/.env
make docker-build
make docker-up
make docker-down

# Backend and worker (backend/; infrastructure and environment must already exist)
pip install -r requirements.txt
flask db upgrade
python run.py
celery -A celery_app worker -l info

# Frontend (frontend/)
npm ci
npm run dev
npm run type-check
npm run build

# Tests (repo root)
make test
make iam-test

# Kubernetes production deployment
make k8s-validate
make k8s-status
```

The Docker entry point is `http://localhost:28080` by default. The configured environments are
`https://taiji.lihao.fun` for local Docker development and
`https://evaluation.fangcunleap.com` for K8s production. They have independent data after the
one-time migration recorded in `deploy/taiji-k8s/MIGRATION.md`.

## Authentication and tenants

- `backend/app/api/auth.py` implements login, registration, callback, session refresh, tenant
  switching, logout and the account-center link.
- `backend/app/auth_context.py` is the compatibility boundary between OIDC sessions and legacy
  JWT auth. Handlers use `login_required()` and current-context helpers from this module.
- OIDC browser requests use the Redis-backed Flask session. Mutating requests require the CSRF
  value returned by `GET /api/v1/auth/me` in `X-CSRF-Token`.
- `users` is global. `tenant_memberships` links a user to a tenant and fixed local role.
  Business models inherit `TenantMixin`; the request's active tenant is applied automatically.
- First OIDC login atomically creates the local user, protected personal tenant, owner
  membership and local `admin` role. The personal tenant is the default active tenant.
- Header tenant switching changes only the current browser session. It does not issue a browser
  token and does not change data in another session.
- Keycloak's `platform_admin` role is only a first-login bootstrap signal. Once the user exists,
  `users.is_superuser` in Taiji is authoritative.
- Platform administrators manage enterprise tenants and platform administrators. They do not
  bypass tenant filtering without a membership in the selected tenant.
- Tenant administrators can add an already provisioned global user directly to their enterprise
  tenant. Keycloak never owns this membership.

The fixed permission matrix is in `backend/app/permissions.py`:

- `admin`: member, task, model, benchmark and audit administration.
- `user`: task and model operations plus benchmark read.
- `guest`: task read only.

Use `@require_permission(Permission.XXX)` on business handlers. Update `Permission`,
`PERMISSIONS_REGISTRY`, `SYSTEM_ROLES` and a migration together when changing the matrix.

## Backend conventions

- `backend/app/__init__.py` creates the Flask app, extensions, request hooks, health checks and
  blueprints. Business APIs mount under `/api/v1`; `/api/health` and `/api/ready` are stable.
- Keep the layering `api/ -> services/ -> models/`. Validate input with Marshmallow and
  `validate_schema()`. Use `ok()`, `created()` and `paginated()` response helpers.
- Raise `BusinessError(ErrorCode.XXX)` from services. The global handler creates the standard
  `{code, message, data}` envelope.
- Cross-tenant maintenance requires an explicit `bypass_tenant_filter()` context. Never use it
  to simplify ordinary request handlers.
- Celery tasks carry `tenant_id`, enter `celery.flask_app.app_context()` and use the explicit
  cross-tenant context only where required.
- `tasks` stores common lifecycle fields. Benchmark and red-team details live in their own tables.
  JSONL logs live below `TASK_LOG_ROOT`; database `log_path` values are relative paths.
- Benchmark suite metadata comes from the engine registry and
  `backend/app/benchmark/engine/inspect_evals/suites.yaml`, not a schema constant.
- Full benchmark execution omits `execution_config.limit`; partial execution passes a positive
  limit. Preserve this distinction when changing form defaults or engine merging.
- Use `safe_requests_get()` and `validate_url()` for user-provided URLs.
- `ModelConfig.api_key` is write-only and must never be returned by an API.
- Record audit entries before the owning transaction's `db.session.commit()`.
- Model changes require an Alembic revision in `backend/migrations/versions/`; do not rely on
  `db.create_all()` outside tests.

## Frontend conventions

- The frontend uses Vue 3, Vite, TypeScript, Pinia, Vue Router hash history, Tailwind CSS 4,
  Reka UI and Lucide icons. Some older utility files remain JavaScript.
- `frontend/src/api/request.ts` is the shared Axios instance. It sends cookies, adds CSRF on
  mutations and clears local auth state on HTTP 401. Do not add Bearer-token storage.
- `frontend/src/stores/auth.ts` owns `/auth/me`, the CSRF token and tenant switching.
- Router gates use `requiresAuth`, `guest`, `requiresPermission`, `requiresSuperuser` and
  `requiresEnterpriseTenant` metadata.
- Prefer project UI primitives in `frontend/src/components/ui/` and Lucide icons. Use semantic
  variables from `frontend/src/assets/theme.css`; preserve dark-mode support.
- Keep API types in `frontend/src/api/types.ts` and run both `npm run type-check` and
  `npm run build` after frontend changes.

## Deployment boundaries

- Compose definitions, images and Nginx configuration live in `deploy/taiji-docker/`. Services
  are PostgreSQL, Redis, Keycloak database initialization, Keycloak, IAM bootstrap, backend,
  frontend and worker. Only frontend publishes host port `28080` by default.
- The OIDC bootstrap creates username `admin` only in a new Realm, assigns a random temporary
  password and prints it once. Read it with `make iam-bootstrap-password`. Never add a fixed
  bootstrap password.
- Kustomize manifests live in `deploy/taiji-k8s/`. Internal services are ClusterIP; the
  `taiji-frpc` pod publishes only the frontend gateway for production.
- K8s images come from `harbor.aixiongan.org.cn:9443/lihao`. Secrets are generated from the
  ignored Docker `.env` and FRP source config; secret manifests are not committed.
- Do not reset PostgreSQL data, `app_data`, `app_logs` or PVCs during routine verification.
- Follow `docs/operations/iam-deployment.md` and `deploy/taiji-k8s/README.md` for releases and
  rollback. The `0021_local_identity` authority migration has no direct Alembic downgrade.
