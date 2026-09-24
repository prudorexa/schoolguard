# SchoolGuard

School Financial Accountability & Loss Prevention Platform. See `docs/schoolguard-blueprint.md` for the full architecture.

## Status: Phase 1 — Foundation

What exists right now:
- Django + DRF backend, JWT auth (`/api/v1/auth/token/`, `/api/v1/auth/token/refresh/`), env-driven settings.
- **`accounts` app**: custom email-based `User` model, data-driven RBAC (`Role`, `Permission`, `RolePermission`, `UserRole` — not hardcoded role checks), `HasRolePermission` DRF permission class, `/api/v1/auth/me/`, `seed_rbac` management command for platform-default roles.
- **`schools` app**: `School` (the tenant), `TenantScopedModel` abstract base every future tenant-scoped model inherits from, `TenantScopedViewSetMixin` (the enforcement point — auto-filters querysets by the caller's school, ignores client-supplied `school` on create), and `Department` as the first real tenant-scoped model/API proving the pattern works.
- **Tenant isolation is tested, not just claimed** — `apps/schools/tests/test_tenant_isolation.py`: cross-school reads return 404 (not 403 — structurally invisible), client can't set another school's ID on create, permission-less users get 403, Super Admins see across schools. Run with `pytest apps/` (see below).
- React + Vite + TypeScript + Tailwind v4 frontend, feature-folder structure, TanStack Query + axios wired with silent token refresh, dev proxy to the backend.
- Docker Compose (Postgres + backend + frontend) and GitHub Actions CI (backend checks + pytest, frontend type-check + build).
- Verified end-to-end over real HTTP: login → JWT → `/me` → create department → list (scoped correctly).

Not built yet: fees/payments (Phase 3) and everything after. Per the blueprint's dependency order, each phase is built and tested against the tenant/RBAC foundation before the next one starts.

### Phase 2 — Students, Classes, Parents

- **`schools` app** gained `AcademicYear`, `Term`, `Class` — same `TenantScopedModel` pattern as `Department`.
- **New `students` app**: `Student` (unique `admission_number` *per school*, not globally — two schools can each have a "S001"), `Parent`, and `StudentParent` (the real many-to-many: a student can have multiple guardians, a parent can have multiple children).
- Cross-tenant guard on `StudentParent`: linking a parent to a student from a *different* school is rejected at the serializer level, tested explicitly — this is the one relationship in this phase where a client could otherwise smuggle a cross-tenant link past the queryset-level filtering alone.
- 10 tests passing total (5 tenant-isolation from Phase 1 + 5 new): same-admission-number-across-schools is allowed, duplicate-within-one-school is rejected, cross-school student listing is blocked, cross-school parent-student linking is blocked, valid linking succeeds.

### Running the backend test suite

```bash
cd backend
DB_ENGINE=sqlite .venv/bin/pytest apps/
```

### Seeding roles/permissions for local dev

```bash
cd backend
DB_ENGINE=sqlite .venv/bin/python manage.py migrate
DB_ENGINE=sqlite .venv/bin/python manage.py seed_rbac
```
Creates the platform-default roles (Super Admin, School Admin, Principal, Accountant, ...) and the `schools.*` permissions currently in use. Extend `PERMISSIONS`/`ROLE_PERMISSIONS` in `apps/accounts/management/commands/seed_rbac.py` as each new module ships.

## Local development

### With Docker (recommended)

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

- Backend: http://localhost:8000/api/v1/health/
- Frontend: http://localhost:5173

### Without Docker

**Backend**
```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
DB_ENGINE=sqlite .venv/bin/python manage.py migrate
DB_ENGINE=sqlite .venv/bin/python manage.py runserver 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

## Repo layout

```
schoolguard/
  backend/     Django project (config/, apps/)
  frontend/    Vite/React/TS app (src/app, src/features, src/lib, ...)
  infra/       (reserved for deploy configs beyond docker-compose)
  docs/        blueprint and architecture decisions
```
