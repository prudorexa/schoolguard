# SchoolGuard — Technical Product Blueprint

**Version:** 1.0 (Pre-implementation)
**Purpose:** Architecture and planning reference for the full build. No code is written against this until it is reviewed.

---

## 1. Product Overview

SchoolGuard is a multi-tenant SaaS platform that gives schools end-to-end financial accountability: every payment collected, every shilling spent, every approval, and every document is tracked, tied to a person, and auditable after the fact.

It is not a school management system with a finance tab bolted on. Finance, audit, and fraud-risk visibility are the product. Students, classes, and parents exist only insofar as they're needed to make the money traceable (who owes what, who paid what).

**Core principle:** *Every shilling entering or leaving a school should be traceable, accountable, and auditable.*

## 2. Problem Statement

Schools — especially in contexts with manual, paper-based, or loosely supervised financial processes — lose money through:

- No single source of truth for income vs. expenditure
- Expenses approved and paid by the same person
- Duplicate or unreconciled payments
- Procurement with no comparison between requested, approved, delivered, and paid amounts
- Missing or unverifiable receipts/invoices
- No audit trail when figures are edited after the fact
- No early-warning system for budget overruns or unusual spending

SchoolGuard's job is to make each of these structurally difficult to do unnoticed — not by adding bureaucracy, but by making the system record what happened, who did it, and whether it matches what should have happened.

## 3. Target Users

| User | Primary need |
|---|---|
| School Admin / Principal | Oversight, approvals, "is anything wrong right now" |
| Accountant | Day-to-day recording of payments and expenses |
| Procurement Officer | Purchase requests → orders → delivery → payment |
| Department Head | Request/track spend for their department |
| Teacher | Limited, mostly read-only, department-scoped |
| Auditor | Read-only, cross-cutting visibility into everything financial |
| Parent | Their own child's invoices, balances, payments, receipts |
| Super Admin (SchoolGuard staff) | Platform-level: onboarding schools, billing, support |

## 4. Functional Requirements (Summary)

Grouped by module — detailed in §12 (Feature Map) and §20 (API).

- Auth & user/role/permission management
- School configuration (multi-tenant)
- Student & parent records
- Fee structures, invoices, payments, receipts, reconciliation
- Expense requests with approval workflow
- Procurement pipeline (request → quotation → PO → delivery → invoice → payment)
- Supplier management
- Inventory tracking
- Budgets with allocation/spend/remaining tracking
- Immutable audit logging of sensitive actions
- Dashboards, financial control center, alerts
- AI: anomaly detection, NL assistant, invoice OCR, summarization, forecasting
- Notifications (in-app, later email/SMS)
- Reporting/export (PDF/Excel/CSV)

## 5. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Security | Backend-enforced RBAC on every endpoint; no trust in frontend checks; hashed passwords; JWT with short-lived access + refresh tokens |
| Auditability | Every mutation to a financial record produces an audit log entry; financial records are never hard-deleted, only reversed/cancelled |
| Tenancy isolation | A query for School A can structurally never return School B's rows |
| Availability | Target 99.5%+ once in production; daily automated DB backups |
| Performance | Dashboard queries return in <2s for a school with ~2,000 students / 5 years of data (achieved via aggregation tables, not live joins over everything) |
| Auditability of AI | Every AI-generated financial claim must be traceable to the backend query/data that produced it |
| Extensibility | New modules (e.g., payroll) addable without restructuring tenancy or auth |
| Compliance-readiness | Structured to support external financial audits (Kenyan school audit norms) even though not itself a compliance product |

## 6. System Architecture

```
                     ┌───────────────────────────┐
                     │   React (Vite/TS) SPA     │
                     │  Axios + TanStack Query    │
                     └──────────────┬────────────┘
                                    │ HTTPS / JWT
                     ┌──────────────▼────────────┐
                     │   Django REST Framework    │
                     │  Views → Serializers →     │
                     │  Services → Models         │
                     │  Permission layer (RBAC)   │
                     └─────┬────────────────┬─────┘
                           │                │
              ┌────────────▼───┐   ┌────────▼─────────┐
              │  PostgreSQL     │   │  AI Service Layer │
              │  (tenant-scoped)│   │ (internal module,  │
              │  + Supabase     │   │  calls Claude via   │
              │   storage/auth  │   │  backend-controlled  │
              │   where useful) │   │  read-only data      │
              └─────────────────┘   │  access functions)   │
                                    └───────────────────────┘
```

**Non-negotiable rule:** the AI layer never touches the database directly. It calls backend service functions that already enforce tenant scoping and role permissions, get back structured data, and generate language from *that* data. It cannot invent numbers because it never has write access and every number it reports came from a service call that can be logged and replayed.

## 7. Frontend Architecture

- **Vite + React + TypeScript**, strict mode on.
- **Routing:** React Router, route-level code splitting, role-aware route guards (a route the user's role can't reach 404s, doesn't just hide the link).
- **Data layer:** TanStack Query for all server state — no manual `useEffect` fetching. Axios instance with interceptors for JWT attach/refresh and centralized error → toast handling.
- **Forms:** React Hook Form + Zod schemas shared between form validation and (ideally) generated from the same shape as backend serializers, to reduce drift.
- **State:** Server state lives in TanStack Query; local/UI state in component state or lightweight context (auth/session, active school, theme). No heavyweight global store needed at this scope.
- **Component structure:**
  ```
  src/
    app/                # routing, providers, layout shell
    features/
      auth/
      students/
      fees/
      expenses/
      procurement/
      suppliers/
      inventory/
      budgets/
      audit-log/
      alerts/
      ai-assistant/
      reports/
      notifications/
      settings/
    components/ui/       # generic, reusable, no business logic
    lib/                 # axios instance, query client, zod schemas, formatters
    hooks/
    types/
  ```
- Each `features/<x>` folder owns its own API calls, hooks, forms, and pages — no cross-feature imports of internals, only through shared `components/ui` and `lib`.
- **Design system:** fintech/enterprise, not "school website." Neutral palette, high-contrast financial figures, red/amber/green status only for genuine risk states, data-dense tables over decorative cards. Dark mode is a stretch goal, not MVP.

## 8. Backend Architecture

Django project split into focused apps — not one giant `core` app:

```
schoolguard/
  config/                 # settings, urls, wsgi/asgi
  apps/
    accounts/              # users, auth, roles, permissions
    schools/                # tenant model, school config, academic years/terms
    students/               # students, parents, classes
    fees/                   # fee structures, invoices
    payments/               # payments, receipts, reconciliation
    expenses/                # expense requests, approval workflow
    procurement/             # requests, quotations, POs, deliveries
    suppliers/
    inventory/
    budgets/
    audit/                   # audit log model + middleware/signal hooks
    alerts/                  # risk/anomaly alert records
    notifications/
    reports/                 # report generation/export
    ai/                      # service functions the AI layer calls; no direct model writes from here either — reuses the same services other apps use
  services/                  # cross-app orchestration where needed (e.g. expense→payment)
```

**Layering inside each app:** `models.py` → `services.py` (business logic, the only place that mutates state) → `serializers.py` (shape, not logic) → `permissions.py` (who can call this) → `views.py` (thin: parse request, call service, return serialized response).

Rule of thumb: **views never contain business logic**, and **serializers never enforce permissions**. This is what makes "you cannot bypass the approval workflow through a direct API call" actually true — the service layer is the only path to a state change, and it re-checks permissions and workflow state regardless of what the frontend sent.

## 9. Database Architecture & Multi-Tenancy

**Approach:** shared database, shared schema, row-level tenancy via a `school_id` foreign key on every tenant-scoped table (simplest to operate at MVP scale; a schema-per-tenant approach can be revisited later if a school demands hard physical isolation).

Enforcement points (defense in depth, not just one filter):
1. A base `TenantScopedModel` abstract model requires `school` on every subclass.
2. A custom DRF permission/mixin injects `school=request.user.school` into every queryset automatically — views cannot "forget" to filter.
3. Serializers never accept `school` as writable input from the client; it's always derived server-side from the authenticated user.
4. Django admin (if used) is also scoped, not a backdoor.
5. Automated tests specifically assert cross-tenant access fails (401/403/empty), not just that same-tenant access works.

## 10. Database Schema (Core Entities)

Grouped by domain; every table below has `id`, `created_at`, `updated_at`, and (except `schools` itself) `school_id`.

**Tenancy & Identity**
- `schools` — name, code, address, contact, subscription plan, status
- `academic_years`, `terms`
- `users` — email, password_hash, is_active, last_login
- `roles`, `permissions`, `role_permissions` (m2m)
- `user_roles` (m2m, since a user could plausibly hold >1 role, e.g. Dept Head + Teacher)
- `login_history`

**People**
- `students` — admission_number (unique per school), name, class, status, parent link
- `parents`, `student_parents` (m2m — supports multiple guardians)
- `classes`, `departments`

**Fees & Payments**
- `fee_structures`, `fee_categories`
- `invoices` — student, term, total_amount, status
- `invoice_items`
- `payments` — invoice, amount, method, reference_number, recorded_by, status
- `receipts` — payment, receipt_number, pdf_url

**Expenses & Procurement**
- `expenses` — department, amount, category, status, requested_by, approved_by
- `expense_items`
- `approvals` — polymorphic-ish: entity_type, entity_id, approver, decision, reason
- `purchase_requests`, `quotations`, `purchase_orders`, `deliveries`, `supplier_invoices`

**Suppliers & Inventory**
- `suppliers` — name, contact, tax_id, status
- `inventory_items`, `inventory_transactions` (received/issued, qty, department)

**Budgets**
- `budgets` — term, department/category, allocated_amount
- `budget_items` / `budget_transactions` — links spend back to a budget for allocated/spent/remaining rollups

**Accountability**
- `audit_logs` — user, action, entity_type, entity_id, previous_value (JSON), new_value (JSON), reason, ip_address, created_at
- `alerts` — type, severity, entity reference, description, status (open/reviewed/dismissed)
- `ai_analysis_records` — what was asked/analyzed, which service functions were called, the response given, for AI auditability

**Notifications**
- `notifications` — user, type, entity reference, read_at

### ERD (description)

- `schools` 1—* everything tenant-scoped.
- `students` *—* `parents` via `student_parents`.
- `students` 1—* `invoices` 1—* `payments` 1—1 `receipts`.
- `departments` 1—* `expenses` 1—* `expense_items`; `expenses` 1—* `approvals` (as one polymorphic approval target among several).
- `purchase_requests` 1—* `quotations`; chosen quotation → `purchase_orders` 1—* `deliveries`; PO also links to `supplier_invoices` → `payments`.
- `budgets` 1—* `budget_items`, which reference `expenses`/`purchase_orders` for the "spent" side of the rollup.
- `audit_logs` references *any* entity generically (entity_type + entity_id) rather than FK-ing every table, so adding new tracked entities doesn't require audit schema migrations.

A full diagram is worth generating in dbdiagram.io or similar once the Phase 1 models are finalized — the description above is enough to start migrations.

## 11. API Architecture

Standard DRF viewsets/routers, versioned under `/api/v1/`. Examples:

```
GET    /api/v1/students/
POST   /api/v1/students/
GET    /api/v1/students/{id}/

GET    /api/v1/fees/invoices/
POST   /api/v1/fees/invoices/
GET    /api/v1/payments/
POST   /api/v1/payments/

GET    /api/v1/expenses/
POST   /api/v1/expenses/
POST   /api/v1/expenses/{id}/approve/
POST   /api/v1/expenses/{id}/reject/
POST   /api/v1/expenses/{id}/pay/

GET    /api/v1/procurement/purchase-requests/
POST   /api/v1/procurement/purchase-requests/{id}/quotations/
POST   /api/v1/procurement/purchase-orders/{id}/receive-delivery/

GET    /api/v1/reports/financial-summary/
GET    /api/v1/audit-logs/
GET    /api/v1/alerts/

POST   /api/v1/ai/ask/                 # NL assistant
POST   /api/v1/ai/summarize-report/
POST   /api/v1/ai/process-invoice/     # OCR extraction
```

Action endpoints (`/approve/`, `/reject/`, `/pay/`) rather than raw `PATCH status=` are deliberate: each maps to a service function that validates the current state, checks the caller isn't the requester (self-approval block), writes the audit log entry, and only then transitions status. A raw PATCH would let a client set any status directly, which is exactly the bypass the spec explicitly forbids.

## 12. Feature Map

| Module | MVP | Post-MVP |
|---|---|---|
| Auth & RBAC | ✅ | 2FA |
| School management | ✅ | — |
| Students & parents | ✅ | — |
| Fees & invoicing | ✅ | Scholarships/bursaries automation |
| Payments & receipts | ✅ (manual + reference-based) | M-Pesa live integration |
| Expenses & approvals | ✅ | — |
| Procurement | Basic PR→PO→delivery | Full quotation comparison tooling |
| Suppliers | Basic CRUD + history | Risk scoring |
| Inventory | Basic stock tracking | Predictive reorder |
| Budgets | ✅ | Multi-year budget planning |
| Audit log | ✅ | — |
| Dashboard | ✅ core KPIs | Custom dashboards per role |
| Financial control center | Basic rule-based alerts | ML-driven anomaly scoring |
| AI assistant | Phase 7 | — |
| AI OCR | Phase 7 | — |
| AI forecasting | Phase 7 | — |
| Notifications | In-app | Email/SMS |
| Reporting/export | CSV | PDF/Excel polish |
| Multi-school SaaS ops | Phase 9 | Billing, usage limits |

## 13. Authentication Architecture

- JWT (access + refresh) via `djangorestframework-simplejwt`.
- Access token short-lived (~15 min), refresh token longer-lived, rotated on use, blacklisted on logout.
- Password hashing via Django's default (PBKDF2/Argon2).
- Email verification required before first login.
- Password reset via time-limited signed token, emailed link.
- Session/login history table logs each login with IP + user agent.
- 2FA (TOTP) is a Phase-1-adjacent stretch item, not blocking MVP.

## 14. RBAC / Permissions Model

Roles are data, not hardcoded `if role == 'accountant'` branches — `roles` and `permissions` tables with a `role_permissions` join, so new roles/permissions can be added without a deploy. A thin custom DRF permission class resolves "does this user's role set include permission X for this action" per view.

Illustrative matrix (✅ = allowed, ❌ = explicitly denied, — = not applicable):

| Action | Accountant | Principal | Auditor | Dept Head | Super Admin |
|---|---|---|---|---|---|
| Record payment | ✅ | — | ❌ (read-only) | — | — |
| Create expense request | ✅ | ✅ | ❌ | ✅ | — |
| Approve expense | ❌ (own dept, see below) | ✅ | ❌ | ❌ | — |
| Approve *own* expense request | ❌ (blocked regardless of role) | ❌ | ❌ | ❌ | — |
| View financial reports | ✅ | ✅ | ✅ | Dept-scoped | ✅ (own school only) |
| View audit logs | ❌ | ✅ | ✅ | ❌ | ✅ |
| Modify audit logs | ❌ | ❌ | ❌ | ❌ | ❌ (no role can — see §15) |
| Delete completed transaction | ❌ | ❌ | ❌ | ❌ | ❌ (reversal only) |
| Manage users/roles | ❌ | ✅ (own school) | ❌ | ❌ | ✅ (platform-wide) |

The self-approval block is enforced in the service layer (`if expense.requested_by == approver: reject`), independent of role — a Principal who happens to have requested an expense still cannot approve their own.

## 15. Audit Architecture

- Every write to a financially sensitive model goes through its service function, which — after the DB transaction succeeds — writes an `audit_logs` row with previous/new value snapshots (as JSON), the acting user, and (for edits, not creates) a required `reason` string.
- Implemented via explicit calls inside services rather than generic model signals, so the audit entry can capture *why*, which a signal can't know.
- `audit_logs` table has no update/delete permission exposed via API to any role, including Super Admin, at the application layer — corrections happen by adding a new reversal entry, not editing history.
- Financial records (payments, expenses once paid) are never hard-deleted: a `status=cancelled`/`reversed` plus a linked reversal record preserves the trail.

## 16. AI Architecture & Data Flow

```
User asks: "How much did we spend on food this term?"
        │
        ▼
Frontend → POST /api/v1/ai/ask/  { question, school context from JWT }
        │
        ▼
ai/views.py → ai/services.py
        │  - resolves intent (which backend query this maps to)
        │  - calls existing, permission-checked service functions
        │    e.g. expenses.services.get_department_spend(school, category="food", term=current)
        │  - gets back real structured data
        ▼
Claude API call (via backend, server-side key)
   prompt = "Given this data: {...}, answer the question in plain language.
             Only use the numbers given. Do not add figures not present."
        │
        ▼
Response returned to frontend, logged in ai_analysis_records
   (question, service calls made, data returned, final answer)
```

Key constraints:
- AI never gets raw DB/model access — only the same service-layer functions a human-triggered view would call, so tenant scoping and permissions apply identically.
- Every AI answer is regenerable/auditable: the `ai_analysis_records` row lets you replay exactly what data backed a given answer.
- Anomaly detection runs as a scheduled backend job (rule-based initially: e.g., "expense > 1.5× department's trailing 6-month average," "same amount+supplier within 48h," "invoice ≠ PO amount by >X%") that writes `alerts` rows. This gets you real, explainable alerts before any ML model is needed — "72% higher than average" is arithmetic, not a model.
- Forecasting (Phase 7, later) can layer statistical/ML methods on top of the same historical aggregates, clearly labeled as estimates in the UI.
- Invoice/receipt OCR uses a document-intelligence step (e.g. Claude's vision input or a dedicated OCR service) to extract structured fields, which then go through the *same* comparison service used for manual entry — the AI extracts, it doesn't decide what's correct.

## 17. Security Architecture

- Every endpoint requires authentication; anonymous access is default-denied (DRF `DEFAULT_PERMISSION_CLASSES`).
- Permission checks happen in the service layer, not just the view/serializer — so even a raw script hitting the API directly can't skip them.
- Input validation via DRF serializers + explicit service-layer sanity checks (e.g., amounts > 0, dates within the active term).
- Rate limiting via DRF throttling classes, tighter on auth endpoints.
- CSRF: N/A for token-auth JSON API consumed by SPA, but cookie-based refresh tokens (if used) get `HttpOnly` + `SameSite` + CSRF protection.
- File uploads (receipts, invoices) validated for type/size, stored in object storage (Supabase storage or S3-compatible), never executed, served via signed URLs.
- Secrets via environment variables only; nothing sensitive in the frontend bundle; the Claude API key lives server-side only.
- HTTPS enforced in production (HSTS).
- Automated PostgreSQL backups with a documented restore procedure, tested — not just scheduled and forgotten.

## 18. Notification Architecture

- `notifications` table, generic entity reference, `read_at`.
- Written by the same services that cause the underlying event (payment recorded → notify accountant/parent; expense pending → notify approver; budget exceeded → notify principal), not a separate polling process.
- MVP: in-app only, fetched via TanStack Query with a polling or (later) WebSocket channel for near-real-time badges.
- Post-MVP: email via a transactional provider, SMS via a local gateway (relevant for M-Pesa-adjacent parent communication in Kenya), push later.

## 19. Reporting Architecture

- Backend "report" endpoints return structured JSON built from aggregation queries (not raw dumps) — the same aggregates power both the dashboard charts and the AI assistant's answers, so numbers can't diverge between the two.
- Export: CSV first (trivial, no extra deps), then server-side PDF (e.g. WeasyPrint) and Excel (openpyxl) once the underlying report queries are stable.
- Reports are always school-scoped and permission-checked identically to any other endpoint — an Auditor can pull the same report shape a Principal can, read-only.

## 20. Multi-Tenant SaaS Architecture (Phase 9)

- `schools.subscription_plan`, `schools.status` (active/suspended/trial) fields drive access gating at the auth-check layer.
- Super Admin role operates across schools for onboarding/support — the *only* role permitted to query across `school_id` values, and every cross-tenant read it performs is itself audit-logged.
- Billing/usage limits (student count caps, storage caps per plan) enforced at the service layer where the relevant resource is created (e.g., student creation checks plan limits before insert).
- School onboarding flow: create school → create first School Admin → seed default roles/permissions → school configures fee structures/departments before going live.

## 21. Recommended Folder Structures

**Backend** — see §8.

**Frontend** — see §7.

**Repo layout (top level):**
```
schoolguard/
  backend/          # Django project (as in §8)
  frontend/         # Vite/React app (as in §7)
  docs/             # this blueprint, ERD exports, ADRs
  infra/            # Dockerfiles, docker-compose, CI workflows
```

## 22. Development Phases

| Phase | Scope |
|---|---|
| 1 — Foundation | Project setup, auth, school mgmt, users/roles/permissions |
| 2 — Students & Parents | Students, classes, parents |
| 3 — Finance | Fee structures, invoices, payments, receipts, reconciliation |
| 4 — Expenses | Expenses, suppliers, approvals, procurement |
| 5 — Accountability | Audit logs, financial controls, alerts, budgets |
| 6 — Analytics | Dashboard, reports, financial analytics |
| 7 — AI | Anomaly detection, AI assistant, invoice extraction, summarization, forecasting |
| 8 — Integrations | M-Pesa, email, SMS, cloud storage |
| 9 — SaaS | Multi-school management, onboarding, billing, usage limits, platform admin |

## 23. MVP Scope

A school could genuinely run on this after Phases 1–5 plus a slice of 6:

- Auth + RBAC (Admin, Principal, Accountant, Dept Head, Auditor, Parent — Procurement Officer role can wait)
- Students/parents/classes
- Fee structures → invoices → payments (manual entry + reference number; M-Pesa API deferred) → receipts
- Expense requests → approval (no self-approval) → paid, with department/budget linkage
- Basic supplier records tied to expenses
- Budgets with allocated/spent/remaining
- Full audit log on all of the above
- Dashboard with the core KPIs (collected, outstanding, spent, budget utilization)
- Rule-based alerts (duplicate payment, budget exceeded, expense >X% above department average)

Everything in §12's "Post-MVP" column, plus all of AI (Phase 7) and SaaS multi-tenancy polish (Phase 9), comes after this is solid for one school.

## 24. Future Features (Beyond Phase 9)

- Payroll module
- Full ML-based anomaly scoring (beyond rule-based)
- Supplier risk scoring
- Custom per-role dashboards
- Multi-year budget planning
- Mobile app (React Native) for parents

## 25. Deployment Architecture

- Containerized: separate Docker images for Django (gunicorn/uvicorn) and the static frontend build (served via CDN/nginx).
- `docker-compose` for local dev (Django, Postgres, frontend dev server).
- CI via GitHub Actions: lint + type-check + test on every PR; build + push images on merge to main.
- Cloud target: any container-friendly host (Render/Railway/Fly.io for early stage, or AWS/GCP later) + managed Postgres (Supabase or RDS) + object storage for uploads.
- Environment separation: `.env`-driven config for local/staging/production, secrets never committed.

## 26. Testing Strategy

- **Backend:** pytest + `pytest-django`. Unit tests per service function (business logic is the highest-value thing to test). Integration tests per critical endpoint, explicitly including: cross-tenant isolation, self-approval rejection, permission denial for under-privileged roles, audit log creation on sensitive mutations.
- **Frontend:** Vitest + React Testing Library for components/hooks; a handful of Playwright end-to-end flows for the critical paths (login, record payment, create+approve expense, view audit log).
- **AI layer:** tests assert the service functions the AI calls return correct data (standard unit tests) and that the AI endpoint never proceeds without a successful, logged service call — not testing the model's language quality, which isn't deterministic.

## 27. Recommended Development Order (Concrete Next Step)

1. Repo scaffold: `backend/` (Django + DRF + Postgres via Docker) and `frontend/` (Vite + TS + Tailwind), CI skeleton.
2. `accounts` + `schools` apps: custom user model, JWT auth, roles/permissions tables, tenant-scoping base model/mixin, and the automated cross-tenant-isolation test *before* any other app is built on top of it — this is the foundation everything else's security depends on.
3. Frontend auth flow (login/register/forgot-password) wired to the above, plus the app shell (sidebar/nav/route guards).
4. Then proceed module-by-module per the Phase table (§22), each module ending with: models → migrations → services → serializers/permissions → views/routes → tests → frontend feature folder → done, before moving to the next.

---

*This blueprint should be treated as a living document — update it as decisions are revisited during implementation, rather than letting the code drift silently away from it.*
