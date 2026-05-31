# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

太极 (Taiji) — Flask 3 + Vue 3 + Celery + Redis full-stack scaffold. Ships with JWT auth (role-based admin/user), Celery-backed example task (webpage analysis), rate limiting via flask-limiter, and a one-shot `docker compose up` deploy. SQLite by default; switch via `DATABASE_URL`.

## Common commands

```bash
# ── Backend dev (from backend/) ──
pip install -r requirements.txt
flask db upgrade                                   # apply migrations
python run.py                                      # Flask on :5000

# ── Celery worker (separate terminal, from backend/) ──
celery -A celery_app worker -l info                # uses module-level `app` in celery_app.py

# ── Frontend dev (from frontend/) ──
npm install
npm run dev                                        # Vite on :5173, proxies /api -> :5000
npm run build                                      # production bundle

# ── Tests (from backend/) ──
python -m pytest tests/ -v                         # all tests
python -m pytest tests/test_auth.py -v             # one file
python -m pytest tests/test_auth.py::test_login -v # one test
make test                                          # repo-root shortcut

# ── Database migrations (from backend/) ──
flask db migrate -m "describe change"              # generate migration from model diff
flask db upgrade                                   # apply
flask db downgrade                                 # roll back

# ── Docker (from repo root) ──
docker compose up -d                               # full stack on :80
docker compose down
make build / make up / make down
```

Default admin (seeded by `docker/entrypoint.sh` on container start): `admin / admin123`.

## Architecture

### Backend (`backend/`)

- **App factory** (`app/__init__.py`): `create_app(config_obj=Config)` wires SQLAlchemy, Flask-Migrate, JWT, flask-limiter, CORS, and Celery. Models are imported eagerly inside `create_app` so SQLAlchemy sees them before `init_app`. Three blueprints are registered under `/api/auth`, `/api/analyze`, `/api/admin`. Health check at `/api/health` lives directly on the app (no blueprint).
- **Celery wiring** (`celery_app.py`): module-level `celery = Celery("taiji")` is created at import time, then `create_celery_app()` runs `create_app()` and calls `init_celery(flask_app)` to copy Flask config into Celery and bind `celery.flask_app`. The Worker entry point is `celery -A celery_app worker` — it picks up the module-level `app = create_celery_app()`. **All Celery task DB work must run inside `with celery.flask_app.app_context():`** (see `app/tasks/analyze_task.py`).
- **Layering**: `api/` (blueprints) → `services/` (business logic, DB writes) → `models/` (SQLAlchemy). Request validation uses **marshmallow** schemas in `app/schemas/` invoked via `validate_schema()` helper (`app/utils/validation.py`) which returns `(parsed, None)` on success or `(None, (response, status))` on failure — handlers must check `error` and early-return.
- **Auth & roles**: JWT identity is stored as a **string** (`create_access_token(identity=str(user.id))`) — always `int(get_jwt_identity())` when reading. Admin endpoints stack `@jwt_required()` then `@admin_required` (from `app/utils/decorators.py`); the decorator re-verifies JWT, loads the user, and checks `is_active` + `role == "admin"`. Roles are defined in `app/utils/roles.py` (`Role.ADMIN` / `Role.USER`).
- **Rate limiting**: shared `limiter` from `app/__init__.py` is used by `analyze_bp` via `@limiter.limit("30 per minute")`. The auth blueprint creates its **own** `Limiter` instance (`auth_limiter` in `app/api/auth.py`) for register (5/min) and login (10/min) — this is intentional, keeping auth limits independent from other endpoints. 429 responses are normalised by the app-level errorhandler in `create_app()`.
- **Response envelope**: every JSON response follows `{"code": int, "message": str, "data": ...}` — `code: 0` means success, non-zero echoes the HTTP status. Stick to this when adding endpoints.
- **Config** (`config.py`): `Config` (production-ish) and `TestConfig` (in-memory SQLite + `CELERY_TASK_ALWAYS_EAGER = True`). `.env` is loaded by `python-dotenv` at import time.
- **Migrations**: managed via Flask-Migrate (Alembic). Migration files live in `backend/migrations/versions/`. Always generate a migration when models change — do not rely on `db.create_all()` outside tests.

### Frontend (`frontend/`)

- **Vue 3 + Vite + Pinia + Element Plus**, hash-mode router. Views: `Home`, `Login`, `Register`, `TaskManagement`, `UserManagement`, `Settings`.
- **`src/api/request.js`** is the only HTTP entry point. It auto-attaches `Bearer <accessToken>` from `localStorage`, and on 401 it transparently calls `/api/auth/refresh` with the refresh token, queues concurrent failed requests, then replays them. If refresh fails, it calls `authStore.logout()` and hard-redirects to `/login`. Any new API module under `src/api/` should import this instance, not raw axios.
- **Router guards** (`src/router/index.js`): `meta.requiresAuth` / `meta.guest`; on first navigation with a token but no in-memory user, it lazy-fetches `authStore.fetchUser()`.
- **Theme system** (`src/assets/theme.css`): plain-CSS variables (no SCSS). Brand palette is ink-black + cinnabar + jade + gold, exposed as `--taiji-primary` / `--taiji-accent` / `--taiji-jade` / `--taiji-gold` and the gradients `--taiji-gradient-{brand,accent,hero}`. The file also overrides Element Plus tokens (`--el-color-primary`, radii, etc.) and defines shadows/radii. **Style new pages with these variables, not hard-coded colors** — they auto-flip under `html.dark`.
- **Dark mode**: toggled by adding/removing `html.dark`; persisted in `localStorage['taiji-theme']`. Initialized in `main.js` (respects `prefers-color-scheme` when no saved value). The user-facing switch lives in the App.vue header and Settings page.
- **Icons**: `@element-plus/icons-vue` is registered globally in `main.js` (`for (const [name, comp] of Object.entries(...)) app.component(name, comp)`) — use `<el-icon><HomeFilled /></el-icon>` directly, no per-file import. **Do not use emoji for UI icons.**
- **Route transitions**: `<transition name="fade-slide">` wraps `<router-view>` in App.vue; the keyframes live in `theme.css`.
- **Dev proxy**: `vite.config.js` proxies `/api` → `http://localhost:5000`. In Docker, Nginx (`docker/nginx.conf`) proxies `/api/` → `backend:5000` and falls back unknown paths to `index.html` for SPA routing.

### Deployment (`docker/`)

Four services: `redis`, `backend` (gunicorn 4 workers via `docker/entrypoint.sh` — runs `flask db upgrade` + `seed_admin` before launch), `worker` (same image, `celery worker` command), `frontend` (multi-stage build → nginx). SQLite DB persists in `./app_data:/app/data` on the host. `backend` and `worker` both wait for redis `healthcheck` to pass.

## Conventions when extending

- **New protected endpoint**: stack `@jwt_required()` (and `@admin_required` if admin-only), parse with a marshmallow schema via `validate_schema`, delegate to a `services/` function, return the standard envelope.
- **New Celery task**: define in `app/tasks/`, import it in `celery_app.py` (the existing `import app.tasks.analyze_task  # noqa: F401` pattern) so the Worker auto-registers it, wrap DB code in `with celery.flask_app.app_context():`.
- **New rate-limited endpoint**: import the shared `limiter` from `app` and use `@limiter.limit(...)`. Only carve out a separate `Limiter` instance if the route has fundamentally different limiting policy (as auth does).
- **Frontend API call**: add a module under `src/api/`, import the default `request` from `./request`, do not bypass the interceptors.
- **Frontend styling**: use `var(--taiji-*)` / `var(--el-*)` variables — never hard-code `#409eff`-style colors, dark mode will break. Section headers use `.page-title` + `.page-icon` pattern (see `TaskManagement.vue`). Page roots use `max-width: 1200px; margin: 0 auto;` to keep wide-screen content centered.
- **Frontend icons**: `<el-icon><IconName /></el-icon>` directly — icons are globally registered, no import needed. Reach for `@element-plus/icons-vue` names rather than ad-hoc SVGs.
