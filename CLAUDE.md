# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

太极 (Taiji) — Flask 3 + Vue 3 + Celery + Redis full-stack AI 模型测评平台。JWT auth (RBAC + revocation)、多租户数据隔离、Celery 异步任务（Benchmark 测评 + 自动红队测评）、flask-limiter 限流，`docker compose up` 一键部署。默认 SQLite，`DATABASE_URL` 可切换。

## Common commands

```bash
# Backend (from backend/)
pip install -r requirements.txt && flask db upgrade && python run.py
celery -A celery_app worker -l info       # separate terminal

# Frontend (from frontend/)
npm install && npm run dev                # Vite on :5173
npm run build

# Tests (from backend/)
conda run -n py12pt python -m pytest tests/ -v
make test                                 # repo-root shortcut

# Migrations (from backend/)
flask db migrate -m "describe change" && flask db upgrade

# Docker (from repo root)
docker compose up -d && docker compose down
```

Default admin: seeded on first start by `docker/entrypoint.sh`. Uses `ADMIN_USERNAME/EMAIL/PASSWORD` env vars; if unset, generates a random password printed once — `docker compose logs backend | grep -A 5 "首次部署"`. Seeded admin is `is_superuser=True`, added to `guest` tenant as owner. Seed is skipped when an admin already exists.

Model configs: `backend/seed_models.py` seeds a preset list of LLM endpoints (Claude, DeepSeek, GLM, GPT, Kimi, MiniMax, Qwen) into the `guest` tenant. Run from `backend/`: `python seed_models.py`. Idempotent — skips entries where `display_name` already exists.

## Architecture

### Backend (`backend/`)

- **App factory** (`app/__init__.py`): `create_app()` wires SQLAlchemy, Flask-Migrate, JWT, flask-limiter, CORS, Celery. All business blueprints mount under `/api/v1/`; `/api/health` is outside the prefix. `@before_request` reads JWT claims into `g.tenant_id / g.is_superuser`. Production rejects weak secrets via `Config._check_secrets()`.
- **Multi-tenancy** (`TenantMixin` + `tenant_memberships`): `users` is global (no `tenant_id`). Memberships link users to tenants with per-tenant roles. Business models inherit `TenantMixin` which auto-injects `WHERE tenant_id = g.tenant_id`. Only system tenant is `guest` (`GUEST_TENANT_SLUG`). `default` tenant removed in migration `0011` — do not reference `DEFAULT_TENANT_SLUG`.
- **RBAC** (`app/permissions.py`): permissions are enum constants seeded into DB. System roles `admin/user/guest` are global+immutable; custom roles are tenant-scoped. Use `@require_permission(Permission.XXX)` on handlers — no `@admin_required` shortcut.
- **Superuser** (`users.is_superuser`): manages tenants via `/api/v1/superadmin/*`, gated by `@superuser_required`. Does **not** bypass tenant filtering on normal endpoints.
- **Auth flows**: registration auto-assigns `user`-role membership in the tenant from `system_setting_service.get_default_registration_tenant_slug()` (client cannot specify tenant). Login selects first active membership. `/auth/switch-tenant` issues new scoped token.
- **JWT revocation**: two channels — (1) Redis blocklist on `jti` for single-token logout; (2) `users.tokens_revoked_at` for user-wide revocation on password/role/membership changes. Revoke marker rounded up to next second to avoid same-second collisions.
- **Task architecture**: `tasks` table stores lifecycle fields + `log_path`. Detail tables per type: `benchmark_tasks`, `red_team_tasks`. `BaseTaskHandler` (`app/handlers/base.py`) auto-generates 5 routes + Celery task; subclasses implement `submit/execute/to_dict`. `TaskRegistry` wires everything in `create_app()`. Task logs are JSONL files under `TASK_LOG_ROOT`, not DB rows.
- **Celery** (`celery_app.py`): all task DB work inside `with celery.flask_app.app_context():`. Tasks must carry `tenant_id` as argument; use `bypass_tenant_filter()` inside tasks.
- **Layering**: `api/` → `services/` → `models/`. Validate with marshmallow via `validate_schema()`. Return via `ok()` / `created()` / `paginated()` — never hand-roll `jsonify`. Raise `BusinessError(ErrorCode.XXX)` from services; global handler converts to envelope `{"code": int, "message": str, "data": ...}`.
- **Rate limiting**: shared `limiter` for most endpoints; `auth_limiter` (separate instance) for auth routes. Both use `_get_client_ip()` for reverse-proxy support.
- **SSRF** (`app/utils/ssrf.py`): use `safe_requests_get()` / `validate_url()` for any user-provided URL. Rejects private IPs, internal hostnames, non-http(s) schemes.
- **Audit logs** (`AuditLog`): does not inherit `TenantMixin`; scope enforced in service. Call `record_audit_log()` before `db.session.commit()` — it only `add()`s, never commits.
- **Model config** (`ModelConfig(TenantMixin)`): per-tenant LLM endpoints. `api_key` is write-only, excluded from all API output. Permissions `model:read/write/delete` granted to `admin+user` roles.
- **Benchmark suites** (`app/schemas/benchmark_schema.py`): `BENCHMARK_SUITES` is the authoritative allowlist for submitted suite names — 46 suites covering safety (HealthBench, AgentHarm, WMDP, StrongREJECT, BeaverTails…), alignment (SycophancyEval, Deceptionbench…), and capability (MMLU, GSM8K, HumanEval, BigCodeBench…). Update this list when adding new evaluation sets.
- **Migrations**: Flask-Migrate/Alembic in `backend/migrations/versions/`. Always generate a migration when models change; do not rely on `db.create_all()` outside tests.

### Frontend (`frontend/`)

- **Stack**: Vue 3 + Vite + Pinia + Element Plus, hash-mode router.
- **HTTP**: `src/api/request.js` is the only entry point — auto-attaches Bearer token, transparently refreshes on 401, redirects to `#/login` on refresh failure. **Never use `window.location.href = '/login'`** (breaks hash routing). `baseURL` is `/api/v1`.
- **Auth store** (`src/stores/auth.js`): holds `/me` payload. `switchTenant()` calls `/auth/switch-tenant`, swaps token, re-fetches `/me`. `originalTenantId` persisted in localStorage.
- **Router guards**: `meta.requiresAuth / .guest / .requiresPermission / .requiresSuperuser`. Lazy-fetches user on first navigation if token present but no in-memory user.
- **Task pages**: `BenchmarkManagement` + `RedTeamManagement` use `activeTasks` polling (2s, MAX_POLLS=30) via reactive proxy (`_updateActiveTask/_getActiveTask`) — never hold raw object references from closures.
- **Theme — Fangcun tokens** (`src/assets/theme.css`): three-tier CSS variables: Primitive (`--violet-*`, `--ink-*`, `--space-*`, `--radius-*`) → Semantic (`--bg-*`, `--fg-*`, `--border-*`, `--shadow-*`, `--color-{success,warning,danger,info}-{bg,fg,border}`) → Element Plus overrides. **Use tokens; never hard-code hex or `--taiji-*` (removed).**
- **Brand**: header displays "方寸AI测评平台 / Fangcun AI Evaluation Platform". Logo mark (`logo-mark-purple.svg`) rendered at 72px. Favicon (`public/favicon.svg`) uses transparent background with the brand mark at `scale(0.45)`.
- **Dark mode**: `applyTheme(isDark)` sets both `html.dark` and `html[data-theme="dark"]`. Persisted in `localStorage['taiji-theme']`.
- **Page conventions**: `.page-shell` wrapper → `.page-header` (eyebrow/title/lede) → `.task-section/.data-section/.settings-card` containers. Status badges use `.status-pill[data-tone="success|warning|danger|progress|neutral"]`, not `<el-tag :type>`. Empty states: dashed border + eyebrow/title/lede + CTA.
- **Icons**: globally registered from `@element-plus/icons-vue` — `<el-icon><HomeFilled /></el-icon>` directly, no per-file import. No emoji for icons.
- **Permission gates**: `const { has } = usePermission()` → `v-if="has('user:write')"`. Superuser UI uses `v-if="authStore.isSuperuser"`.
- **Voice**: no emoji, no exclamation marks, no empty superlatives in UI copy.

### Deployment (`docker/`)

Services: `redis`, `backend` (gunicorn 4 workers, runs migrations + conditional admin seed), `worker` (same image, celery, `RUN_MIGRATIONS=false`), `frontend` (nginx). SQLite in `./app_data:/app/data`; logs in `./app_logs:/app/logs` (shared by backend + worker).

**Do not reset `app_data/taiji.db` during routine verification.**

## Conventions when extending

- **New model**: extend `TenantMixin`; use `foreign_keys="MyModel.tenant_id"` (string, not bare name) for `db.relationship`.
- **New endpoint**: `@jwt_required()` + `@require_permission(...)` → `validate_schema()` → service → `ok()/created()/paginated()`. Mount under `/api/v1/`. Superuser-only goes in `superadmin.py`.
- **New permission**: add to `Permission` + `PERMISSIONS_REGISTRY` + `SYSTEM_ROLES`; regenerate migration.
- **New system setting**: add to `SETTING_DEFINITIONS` in `system_setting_service.py`.
- **Cross-tenant query**: `with bypass_tenant_filter():`.
- **New Celery task**: define in `app/tasks/`, import in `celery_app.py`. Take `tenant_id` as arg; use `app_context` + `bypass_tenant_filter`.
- **Rate limit**: use shared `limiter`; only create separate instance for fundamentally different policy (as auth does).
- **SSRF**: `safe_requests_get()` + `validate_url()` for any user-provided URL.
- **Frontend API**: new module under `src/api/`, import `request` from `./request`.
- **Token revocation on mutations**: set `user.tokens_revoked_at = _revoke_marker()` whenever role/membership/password/active changes.
- **Audit logging**: call `record_audit_log()` before `db.session.commit()` in service functions that mutate users/tenants/memberships.
