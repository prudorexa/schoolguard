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

Not built yet: OCR invoice processing, forecasting (rest of Phase 7), integrations (Phase 8), full SaaS multi-tenancy (Phase 9).

### Phase 7 — AI Financial Assistant

**Important caveat, stated plainly:** this sandbox's network policy does not include `api.anthropic.com`, so while the integration is implemented correctly against the documented Anthropic SDK interface, **the actual live API call has not been exercised end-to-end** the way everything else in this project has been proven with real HTTP round-trips. Everything on *our* side of that boundary — which is also where almost all of the risk actually lives — is tested for real. Before relying on this in production, set a real `ANTHROPIC_API_KEY` and confirm the two live Claude calls (tool selection, then grounded answer) behave as expected.

- **New `ai` app**, built exactly to the blueprint's AI data-flow requirement: Claude never touches the database. It picks one of a small, explicit, parameterized set of **whitelisted tools** (`ai/tools.py`) — `get_financial_summary`, `get_financial_alerts`, `get_budget_status`, `get_pending_expense_approvals`, `get_top_expenses` — each of which is a thin wrapper around an **existing, already-tested service function** from `dashboard`/`budgets`/`expenses`. The AI layer adds no new data-access logic of its own; there is no code path from a Claude tool call into raw SQL, the ORM directly, or another school's data.
- **Two-step grounding, per the blueprint**: Claude sees the question and picks a tool → we execute it ourselves against the caller's own school → Claude sees *only* the JSON that came back, with an explicit system-prompt instruction to answer using only those numbers and never invent a figure. Verified with a fake injected client that the second call's message body actually contains the real computed data, not just that a plausible-looking number appears in a canned test response.
- **Every question is logged** (`AIAnalysisRecord` — the blueprint's `ai_analysis_records` entity): question, which tool was called with what parameters, exactly what data came back, the final answer, and any error — so a wrong-looking answer can be traced to either a real bug elsewhere or a language-generation issue, not left as a mystery. Read-only in Django admin, same as the audit log.
- **Tested via dependency injection**: `ask_assistant(..., client=...)` accepts any object shaped like the real `anthropic.Anthropic()` client, so the tool-routing, tenant-scoping, grounding, logging, and error-handling logic all have real test coverage without needing network access. 9 tests, including one that deliberately gives two different schools a department with the *same name* ("Science") and confirms the tool only ever returns the caller's own school's budget.
- **Configuration failures are clean, not crashes** — verified live over real HTTP: with no `ANTHROPIC_API_KEY` set (the default state for anyone who clones this repo), `POST /api/v1/ai/ask/` returns a proper `503` with an actionable message, not a raw exception.
- Gated by `ai.use_assistant` like every other permission in this project — School Admin, Principal, and Accountant have it by default; it isn't a side door around the RBAC system.
- 9 new tests (75 total across the project).

**Deliberately not built in this pass**: invoice/receipt OCR (needs document/vision handling — a genuinely separate piece of work) and forecasting (needs historical data volume this demo doesn't have). Report summarization could reuse the same `ask_assistant` pattern almost directly and would be a natural next addition.

To try it: add a real key to `backend/.env` (`ANTHROPIC_API_KEY=sk-ant-...`), then `POST /api/v1/ai/ask/` with `{"question": "..."}` as a user with `ai.use_assistant`.

### Frontend — real screens, wired to the real backend (not a mock)

Login, the dashboard, and the audit log are fully built and consume the actual API — no placeholder or fake data anywhere in these three screens. Verified end-to-end through the real Vite dev server proxy: login → JWT → `/auth/me` → dashboard summary → alerts, all returning real data from the backend.

- **Design**: a ledger/fintech aesthetic, not a generic SaaS-card template — dark permanent sidebar (`#14171F`) for wayfinding, warm-paper content area (`#F6F5F1`), Fraunces serif for KPI figures and page titles (the numbers are the hero), IBM Plex Sans for everything else, a deep teal-green accent (`#1F6F5C`) rather than the generic terracotta/acid-green AI-default. Alerts use a left-rule + color for severity, not badge pills; transactions use hairline dividers, not shadowed cards.
- **Auth**: `lib/auth.tsx` — real login against `/auth/token/`, JWT stored and silently refreshed (`lib/api.ts`, unchanged from Phase 1), `/auth/me/` populates the current user/roles, protected routes redirect to `/login` when not authenticated.
- **Dashboard** (`features/dashboard/`): consumes `/dashboard/summary/` and `/dashboard/alerts/` directly — the same computed, never-stored numbers proven in Phase 6's backend tests.
- **Audit Log** (`features/audit/`): consumes the real `/audit-logs/` endpoint, read-only, tenant-scoped, exactly as built in Phase 5.
- **Other nav items** (Students, Fees, Expenses, Procurement, Suppliers, Budgets) — all fully built since, see the "Frontend" sections further down this README for each.

### Frontend — Students (list, create)

- **`features/students/`**: list view and a create form (admission number, name, optional class). Closes a real gap — before this, the only way to get a student into the system was `manage.py shell`, which meant the Fees screen built in the previous session was untestable as a real user flow.
- Duplicate admission numbers are rejected with the exact backend message (`{"admission_number": [...]}`) surfaced on the form — verified live this time *before* writing the parsing code, not after, applying the lesson from the Fees error-shape bug: serializer-level field errors (`validate_admission_number`) and service-layer workflow errors (`raise ValidationError(str(exc))`) are genuinely different DRF response shapes, and both are now handled correctly rather than assumed to match.
- Verified live end-to-end: seeded a school with zero students, confirmed the list was empty, created a student through the exact API call the form makes, confirmed it immediately appeared and was usable in the Fees invoice form from the previous session — proving the two modules actually connect, not just that each works in isolation.

### Frontend — Procurement (the full pipeline, one flowing view)

- **`features/procurement/`**: list + create for Purchase Requests, and a single detail page that follows the actual shape of the workflow rather than splitting it across five disconnected screens — PR info & workflow actions, then (once approved) quotations from multiple suppliers with an "Issue PO" action per quote, then (once a PO exists) delivery recording, then supplier invoice recording, then the discrepancy report — each section appearing only once the previous stage makes it relevant.
- Quotations and purchase orders aren't filterable server-side by purchase request, so the frontend fetches the (small, tenant-scoped) full list and filters client-side — a pragmatic, explicit choice, not an oversight.
- **Verified the entire pipeline live, start to finish, through the real proxy, using the exact calls each button/form makes**: PR created with a correctly computed estimated total → submitted → approved by a different user (Officer submits, Principal approves — real separation, not simulated) → two competing quotations added and correctly listed → PO issued at the cheaper quote's exact amount → delivery recorded → a deliberately mismatched supplier invoice recorded → discrepancy report correctly flagged the 17.9% variance, matching the exact backend behavior proven back in Phase 4b. No bugs found this time — the error-shape and permission lessons from Suppliers/Budgets/Fees held up without needing another fix.

### Frontend — Procurement (the full pipeline, one detail page)

- **`features/procurement/`**: list + create for Purchase Requests (same workflow pattern as Expenses: draft → submit → approve/reject, self-approval blocked), and a single rich detail page that carries the request through the *entire* remaining pipeline in place — quotations from multiple suppliers, issuing a PO from the selected quote, recording delivery, recording the supplier's invoice, and the discrepancy report, each section appearing only once the previous stage is actually done (no quotation form before approval, no delivery section before a PO exists, no discrepancy check before an invoice is recorded).
- **Found this feature-folder already substantially written** (same situation as the `fees` backend app earlier) — reviewed every file line by line against the actual serializer fields and the lessons learned from every error-shape bug this session (bare array / `non_field_errors` / `detail`, all three already handled correctly) before trusting it, rather than assuming it was correct because it looked right.
- **Verified the entire pipeline live, through the real proxy, as one continuous run**: created a PR (estimate computed as 5 × 4,000 = 20,000), submitted, approved by a different user, two competing quotes submitted (19,500 and 21,000), PO issued at the cheaper quote's exact amount, delivery recorded, then a deliberately mismatched supplier invoice (23,000) recorded — and the discrepancy endpoint correctly flagged it: *"Invoice amount (23000.00) differs from PO amount (19500.00) by 17.9%, above the 5.0% threshold."* Not a separate unit test — the literal sequence of calls the real buttons make, back to back.

This closes out every module from the blueprint's core financial phases (1–6) with a working frontend, not just a tested backend.

### Frontend — AI Assistant (chat screen)

- **`features/assistant/`**: a chat-style page, distinct from the list/form pattern used everywhere else since the interaction genuinely is different. Every answer shows a small "Grounded in: `tool_name`" caption underneath — making the backend's tool-whitelist architecture visible to the person using it, not just something described in this README.
- **Treats "not configured" as an expected, explained state, not a generic error.** Since the real-world default (no `ANTHROPIC_API_KEY` set) is a `503`, the chat shows it as a distinct amber message — *"An administrator needs to add an ANTHROPIC_API_KEY to the backend to enable this feature"* — rather than a red failure that looks like something's broken. Verified live through the real proxy, exact call the send button makes: `503` with the backend's actionable detail message, and separately, a Teacher (no `ai.use_assistant` permission) correctly getting `403`.
- Same honest caveat as the backend section above: the actual Claude API call itself is implemented but not exercised end-to-end in this sandbox (no network access to `api.anthropic.com`). What's verified here is everything on this side of that boundary — the request the button sends, and both realistic response states (not configured, no permission) rendering correctly.

### Frontend — Login error clarity fix

`LoginPage` previously showed "Incorrect email or password" for *every* failure, including the frontend simply being unable to reach the backend at all. That's actively misleading — someone with the exact right credentials would see the same message as someone who typo'd their password. Now distinguishes "no response received" (network/backend-unreachable) from "got a 401" (actually wrong credentials) from anything else.

### Frontend — Budgets (list with live utilization, create)

- **`features/budgets/`**: list view where each row independently fetches and renders its own computed status (allocated/spent/remaining/utilization%) via the real `/budgets/{id}/status/` endpoint — a progress bar that changes color exactly at the same thresholds the backend flags (`is_near_threshold` → amber, `is_over_budget` → red), and a create form.
- **Confirmed the utilization math live, end to end**: created a 40,000 budget, approved a 34,000 expense against the same term through the real workflow (dept head requests → submits → admin approves), and the status endpoint correctly returned 85% utilization with `is_near_threshold: true` — exactly matching what the progress bar renders as amber.
- **Another real finding, this time explaining *why* the Suppliers bug existed the way it did**: attempting a duplicate `(term, department)` budget returns `{"non_field_errors": [...]}`, not the bare array seen with Suppliers' duplicate name. Reason, confirmed by testing rather than guessed: DRF's automatic `UniqueTogetherValidator` **can** auto-generate for `Budget` because both constraint fields (`term`, `department`) are real, present serializer fields — unlike the "unique per school" models, where `school` is deliberately excluded from the serializer (set server-side, never client-writable) and DRF has nothing to build a validator from. This confirms the root cause behind the earlier backend fix precisely, and the frontend's error parser now handles both shapes rather than assuming one.

### Frontend — Suppliers (list, create) — and a real backend bug found and fixed along the way

- **`features/suppliers/`**: list view and a create form (name, contact person, phone, email).
- **This surfaced a genuine, systemic backend bug, not just a frontend edge case.** Testing the duplicate-name path live (same discipline as every module before this) returned a raw Django 500 debug traceback instead of a clean validation error. Root cause: DRF's `ModelSerializer` only auto-generates client-facing uniqueness validation for the older `Meta.unique_together` style — **not** for `Meta.constraints = [UniqueConstraint(...)]`, which is what every tenant-scoped model in this project actually uses (`Department`, `Class`, `AcademicYear`, `Term`, `FeeCategory`, `Supplier`, and more). Every one of them had this exact gap; `Student` was the only exception, because it happens to have a custom `validate_admission_number` written by hand.
- **Fixed centrally, not per-model**: `TenantScopedViewSetMixin.perform_create` (the one path every plain-CRUD viewset already shares) now catches `IntegrityError` and converts it to a clean 400. One change fixes every affected model at once, rather than writing a bespoke `validate_name()` for each. Added two regression tests against `Department` (representative of the whole class of models) and reran the full 66-test suite to confirm nothing else broke.
- Verified live, twice: once directly confirming the 500 before the fix, once after confirming a clean `400` — through the exact call the real `NewSupplierPage` form makes, via the actual Vite proxy.

- **`features/fees/`**: invoice list, a create form (student/term pickers + dynamic fee-category line items), and a detail view showing total/paid/balance with a record-payment form.
- **Overpayment rejection is visible to a real user, not just a test assertion.** Tried to pay 99,999 against a 15,000 balance through the exact endpoint the form calls and got a proper on-screen message, not a silent failure or generic error.
- **Caught and fixed a real bug in my own error-handling code during this live test**: DRF serializes a `ValidationError` raised from a plain string (which is every workflow rule in `services.py`, across both `fees` and `expenses`) as a **bare JSON array** — `["message"]` — not `{detail: "..."}` or `{non_field_errors: [...]}` like I'd assumed when writing the Expenses page earlier. That assumption meant real backend error messages (the overpayment reason, the self-approval reason) would have silently fallen through to a generic fallback message instead of showing the actual reason. Verified the exact response shape live before fixing, fixed the parsing logic in both `InvoiceDetailPage` and `ExpenseDetailPage`, then re-verified.

- **`features/expenses/`**: list view, a create form with dynamic line items (client-side total is a preview only — the server-computed total is always what's authoritative, matching the backend's design), and a detail view where every workflow action (submit/approve/reject/mark-paid/cancel) is a real call to the real endpoint.
- **The self-approval block is visible in the UI, not just enforced silently on the backend** — if you're viewing your own pending request, the page tells you upfront you won't be able to approve it yourself; if the button is clicked anyway (or the rule is hit some other way), the 403 from the backend surfaces as a clear on-page message rather than failing silently.
- **Found and fixed a real, pre-existing RBAC gap while building this**: `Department Head`, `Accountant`, and `Procurement Officer` could all create expenses/purchase requests tied to a department, but none of them had `schools.view_departments` — so none of them could have populated a department picker. Fixed in `seed_rbac.py`; confirmed live that a Department Head can now see the department list and everything downstream still enforces the same permissions correctly (self-approval block, 403 on unauthorized approve).
- Verified end-to-end through the actual Vite proxy the browser uses (not just backend curl): login → view departments → create → submit → blocked self-approval → real approval by a different user with the right permission.

To see it running: start the backend (`DB_ENGINE=sqlite .venv/bin/python manage.py runserver`) and frontend (`npm run dev`) per the instructions above, seed a user via `manage.py shell` (see any Phase's walkthrough above for the pattern), and log in at `http://localhost:5173`.

### Phase 6 — Analytics: financial dashboard + Financial Control Center

- **New `dashboard` app, deliberately model-less** — every number is computed fresh from `fees`/`expenses`/`procurement`/`budgets` at request time, never stored, so nothing here can drift out of sync with the transactions behind it.
- **`GET /dashboard/summary/`**: total collected, total expenses, outstanding fees, net position, aggregate budget utilization, pending approval count, recent transactions (merged from payments and paid expenses, sorted). Confirmed live against real data — collected/outstanding/net position all matched the underlying invoice and payment exactly.
- **`GET /dashboard/alerts/`** — the Financial Control Center from the blueprint, and every alert is plain arithmetic against a documented rule, never a model output: budget exceeded (critical), invoice-vs-PO mismatch reusing the Phase 4 discrepancy check (critical), duplicate payment — same invoice + amount + method recorded within 24 hours of each other (critical), expenses awaiting approval (warning), overdue invoices — term ended, balance still outstanding (warning).
- **Deliberately does not include a statistical "unusual spending" alert.** That needs a baseline/model and is explicitly the AI anomaly-detection layer's job (blueprint Phase 7), not something to hand-roll here as a fake heuristic.
- 10 new tests (64 total across the project): summary math against real payments/expenses, permission gating, each alert rule firing and *not* firing under the right conditions (including a same-user self-approval attempt in my own test fixture getting correctly rejected by the Phase 4 rule — caught while writing these tests, not an app bug), and cross-school alert isolation.

### Phase 5 — Accountability: audit log + budgets

- **New `audit` app**: `AuditLog` is genuinely append-only — no create/update/delete exposed anywhere, including Django admin (`has_add_permission`/`has_change_permission`/`has_delete_permission` all return `False` even for staff). The API is a `ReadOnlyModelViewSet`. `log_action()` is the single entry point every other app calls.
- **Retrofitted into real mutations, not just new ones going forward**: `fees` (payment recorded/reversed, with previous/new status and required reversal reason), `expenses` (approved/rejected/paid, with the amount at time of approval), `procurement` (PR approved/rejected, PO issued). Confirmed live — approving an expense produces a real, queryable log entry with the amount and who approved it.
- **New `budgets` app**: `Budget` (allocated amount per department + term). `spent_amount` is deliberately **not a stored counter** — `budget_status()` computes it fresh from real `Expense` rows every call, so it can never drift out of sync with reality. Returns allocated/spent/remaining/utilization%/over-budget/near-threshold.
- **Caught a real design bug while testing this**: I'd initially inferred which term an expense belonged to from its wall-clock `created_at` timestamp compared against the term's date range. That's fragile — an expense entered a few days after term-end wouldn't count toward that term's budget in production, not just in the test. Fixed by adding an explicit, nullable `term` FK directly on `Expense` rather than inferring it, and confirmed live: an 85,000 expense against a 100,000 budget correctly shows 85% utilization and `is_near_threshold: true`.
- 13 new tests (54 total across the project): audit entries created with correct actor/reason/before-after values, audit log tenant-scoped and permission-gated, no write path exists on the audit endpoint (403, checked before DRF even resolves a handler), budget spend only counts `approved`/`paid` expenses (not draft/pending), near-threshold and over-budget flags, and duplicate-budget-per-term-and-department rejected at the DB level.

### Phase 4b — Procurement pipeline

- **New `procurement` app**: `PurchaseRequest`/`PurchaseRequestItem` → `Quotation` (multiple suppliers, one selected) → `PurchaseOrder` (amount fixed at issue time from the winning quote) → `Delivery` → `SupplierInvoice`. Same status-machine discipline as `expenses`: every transition is its own endpoint through `services.py`, no PATCH/PUT/DELETE.
- Same self-approval block as expenses, same pattern, tested the same way (service-level and live HTTP).
- **The actual point of this module** — comparing requested vs approved vs delivered vs invoiced and flagging mismatches — is a real, working endpoint: `GET /purchase-orders/{id}/discrepancy/`. It never blocks anything or accuses anyone; it just surfaces the numbers for a human to review, matching the blueprint's "flag for human review" principle. Confirmed live: recorded a supplier invoice 17.9% above the PO amount and got it flagged with the exact percentage.
- **Applied the lesson from the expenses bug proactively this time**: `get_permissions()` is overridden per-action from the start, and the test fixture deliberately mirrors the real seed data's permission shape (approve-only Principal, create-only Officer) rather than a more-permissive test role, specifically to catch that class of bug before it ships rather than after.
- 10 new tests (51 total across the project): computed estimates, self-approval block (service + API), approve-only role working correctly, full pipeline happy path, discrepancy flagging, workflow-order enforcement (can't quote against an unapproved PR, can't double-issue a PO), and cross-tenant isolation on purchase requests and supplier selection.

### Phase 4 — Expenses & Suppliers (procurement pipeline is next)

- **New `suppliers` app**: `Supplier`, tenant-scoped CRUD. Kept deliberately light — derived fields like total-paid/risk-scoring come later once there's real transaction history to compute from, not stored counters that could drift.
- **New `expenses` app**: full status machine — `draft → pending_approval → approved → paid`, with `rejected` and `cancelled` off-ramps. Every transition is its own endpoint (`/submit/`, `/approve/`, `/reject/`, `/mark-paid/`, `/cancel/`) routed through `services.py`; PATCH/PUT/DELETE are disabled entirely, so there's no way to skip a step by hitting the API differently.
- **The self-approval block is the core rule of this module** and it's enforced in the service layer, unconditionally — `approve_expense`/`reject_expense` check `requested_by == approver` regardless of what permissions the approver holds. Tested both at the service level and through the live API.
- **Separation of duties, real not cosmetic**: `expenses.create_expenses`, `expenses.approve_expenses`, and `expenses.record_expense_payment` are three separate permissions. Accountant holds create + record-payment but not approve; Department Head holds create only; Principal holds approve only. Confirmed live: Accountant can mark an approved expense paid but gets 403 trying to approve one.
- **Caught and fixed a real bug while building this**: the viewset's class-level permission check was tied to `expenses.create_expenses`, which silently blocked the Principal (approve-only, no create permission) from using the approve action at all — a live HTTP test surfaced it immediately. Fixed with a per-action `get_permissions()` override, and added a regression test (`test_approver_without_create_permission_can_still_approve`) using a role shaped exactly like the real seed data, so the original test suite's overly-permissive fixture can't hide this class of bug again.
- 11 new tests (41 total across the project).

### Phase 2 — Students, Classes, Parents

- **`schools` app** gained `AcademicYear`, `Term`, `Class` — same `TenantScopedModel` pattern as `Department`.
- **New `students` app**: `Student` (unique `admission_number` *per school*, not globally — two schools can each have a "S001"), `Parent`, and `StudentParent` (a real many-to-many: multiple guardians per student, multiple children per parent).
- Cross-tenant guard on `StudentParent`: linking a parent to a student from a *different* school is rejected at the serializer level, tested explicitly.

### Phase 3 — Fees & Payments (the first module that's actually money)

- **New `fees` app**: `FeeCategory`, `FeeStructure`, `Invoice`/`InvoiceItem`, `Payment`, `Receipt`.
- `Invoice.total_amount` is **never client-supplied** — `POST /invoices/` takes line items, and `services.create_invoice_for_student` computes the total server-side. There's no code path where a client can set a total that doesn't match its items.
- `Payment` amounts are checked against the invoice's real outstanding balance before being accepted — **overpayment is rejected outright** (tested), not silently allowed.
- Recording a payment **atomically generates a `Receipt`** (`RCT-<SCHOOL_CODE>-NNNNNN`) — there's no way to have a completed payment with no receipt.
- Payments are **never deleted or edited** — a wrong payment is reversed (`POST /payments/{id}/reverse/`, reason required), which flips status to `reversed` and recomputes the invoice's balance, but the row and its history stay.
- **Separation of duties, enforced not just described**: the `Accountant` role can record payments but does **not** get `fees.reverse_payments` — reversal needs a role with that permission explicitly (School Admin/Principal in the seed data). Tested: an Accountant hitting `/reverse/` on their own recorded payment gets 403.
- `InvoiceViewSet`/`PaymentViewSet` disable PATCH/PUT/DELETE entirely (`http_method_names`) — the only way to change a payment's state is through the `reverse` action, which goes through the service layer, not a raw field edit.
- 10 new tests (30 total across the project): computed totals, balance math, receipt generation, overpayment rejection, reversal restoring balance without deleting the payment, reversal requiring a non-empty reason, the separation-of-duties 403, and cross-tenant invoice/payment isolation (paying another school's invoice returns 404, same "structurally invisible" pattern as Phase 1/2).

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
