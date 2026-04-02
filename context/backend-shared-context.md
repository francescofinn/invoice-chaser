# Backend Shared Context

This file is the shared coordination record for parallel backend work. Every thread should update it when starting work, changing scope, getting blocked, finishing a handoff gate, or discovering contract drift.

If two threads disagree, this file becomes the temporary source of truth until the source plan is updated.

## Update Protocol

- Update the relevant workstream row before editing code.
- Add a short entry to the activity log when starting, blocking, unblocking, or finishing a meaningful slice.
- Record any change to schemas, statuses, route shapes, or service signatures in the decision log.
- Do not mark a workstream complete until tests for that slice pass.

## Global Non-Negotiables

- Invoice statuses: `draft`, `sent`, `viewed`, `partially_paid`, `paid`, `overdue`
- Money uses `Decimal` and `Numeric(10, 2)`, never float persistence
- `Invoice.line_items` stays JSON list-of-dicts
- `Invoice.token` stays UUID-backed public identifier
- `GET /invoices/public/{token}` must be declared before `GET /invoices/{id}`
- Stripe webhook must verify from raw request body
- Scheduler follow-ups use insert-before-send idempotency
- Frontend response shapes must stay aligned with `docs/plan-backend.md`

## Contract Freeze Checklist

- [x] Environment variable names locked
- [x] SQLAlchemy model fields and nullability locked
- [x] Pydantic response shapes locked
- [x] Shared invoice-total calculation approach locked
- [x] Stripe PaymentIntent lifecycle rules locked
- [x] Email and AI service signatures locked

## Workstream Board

| Workstream | Scope | Primary Files | Depends On | Status | Owner | Branch | Last Updated | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Foundation Freeze | Settings, models, schemas, Alembic, backend skeleton | `backend/database.py`, `backend/models.py`, `backend/schemas.py`, `backend/alembic/*`, `backend/requirements.txt` | None | Complete | Codex | `emilio` | 2026-04-02 | Foundation landed with env loading, helpers, migration config, and tests |
| A | Clients CRUD | `backend/routers/clients.py` | Foundation Freeze | Complete | Codex | `emilio` | 2026-04-02 | CRUD complete with `404`, `409`, and test coverage |
| B | Invoice CRUD plus public payment flow | `backend/routers/invoices.py` | Foundation Freeze, Service Interface Freeze | Complete | Codex | `emilio` | 2026-04-02 | CRUD, send flow, public token flow, and Stripe reuse/create rules are implemented |
| C | External services | `backend/services/email.py`, `backend/services/ai.py` | Foundation Freeze | Complete | Codex | `emilio` | 2026-04-02 | Service signatures are stable and tested |
| D | Webhooks and scheduler | `backend/routers/webhooks.py`, `backend/services/scheduler.py` | Foundation Freeze, B, C | Complete | Codex | `emilio` | 2026-04-02 | Webhook idempotency and follow-up scheduler behavior are implemented and tested |
| E | Dashboard, app wiring, seed, local verification | `backend/routers/dashboard.py`, `backend/main.py`, `backend/seed.py` | Foundation Freeze, B, D | Complete | Codex | `emilio` | 2026-04-02 | Summary endpoint, app wiring, seed script, and verification are complete |

## Handoff Gates

| Gate | Description | Required Before | Status | Owner | Notes |
| --- | --- | --- | --- | --- | --- |
| G1 | Contract Freeze: models, schemas, env vars, statuses, migration names | All parallel streams | Complete | Codex | Locked in code and reflected in tests |
| G2 | Service Interface Freeze: email and AI function signatures | Workstream B and D integration | Complete | Codex | `send_invoice_email` and `generate_follow_up_email` are implemented and wired |
| G3 | Payment Flow Freeze: PaymentIntent create/reuse semantics and webhook status rules | Workstream D and E validation | Complete | Codex | Public portal reuse/create rules and webhook idempotency verified |
| G4 | API Freeze: responses checked against the source plan examples | Frontend integration confidence | Complete | Codex | Invoice and dashboard response shapes are covered by tests |

## Merge-Conflict Hotspots

- `backend/models.py`
- `backend/schemas.py`
- `backend/main.py`
- `backend/database.py`
- `backend/routers/invoices.py`

## Decision Log

| Date | Decision | Impacted Areas | Owner | Notes |
| --- | --- | --- | --- | --- |
| 2026-04-02 | Parallel delivery begins only after a short foundation freeze. | All backend workstreams | Codex | Prevents schema and contract drift |
| 2026-04-02 | `backend/routers/invoices.py` should stay single-owner during active development. | Invoice CRUD, send flow, public flow | Codex | Minimizes merge conflicts in the biggest hotspot |

## Active Blockers

| Date | Workstream | Blocker | Waiting On | Owner | Status |
| --- | --- | --- | --- | --- | --- |
| 2026-04-02 | None | No active blockers yet | N/A | Unassigned | Open |

## Test Ledger

| Date | Workstream | Test Scope | Result | Owner | Notes |
| --- | --- | --- | --- | --- | --- |
| 2026-04-02 | None | No tests run yet | Pending | Unassigned | Fill this in as each slice lands |
| 2026-04-02 | Full backend | `pytest -q` | Passed | Codex | 26 tests passed |
| 2026-04-02 | Full backend | `pytest --cov=. --cov-report=term-missing` | Passed | Codex | 92% total coverage in the backend test run |
| 2026-04-02 | Foundation / ops smoke | `alembic upgrade head` against SQLite smoke DB | Passed | Codex | Initial migration applied cleanly |
| 2026-04-02 | Foundation / ops smoke | `python seed.py` against SQLite smoke DB | Passed | Codex | Seeded 3 clients and 3 invoices |
| 2026-04-02 | Plan revalidation | `pytest -q` | Passed | Codex | 27 tests passed after contract-hardening fixes |
| 2026-04-02 | Plan revalidation | `pytest --cov=. --cov-report=term-missing` | Passed | Codex | Coverage remained at 92% after the revalidation pass |

## Activity Log

| Date | Workstream | Update | Owner |
| --- | --- | --- | --- |
| 2026-04-02 | Planning | Created shared backend coordination file and initialized workstream structure. | Codex |
| 2026-04-02 | Foundation Freeze | Began single-thread backend implementation and locked the current branch owner to `emilio`. | Codex |
| 2026-04-02 | Delivery | Completed the backend implementation, test suite, migration smoke test, and seed smoke test. | Codex |
| 2026-04-02 | Revalidation | Recompared the implementation to the source backend plan, hardened invoice response serialization for `line_items`, and narrowed webhook signature error handling. | Codex |

## Thread Handoff Template

Use the template below when a thread pauses or hands off work:

```md
### Handoff
- Workstream:
- Branch:
- Files touched:
- Completed:
- Remaining:
- Tests run:
- Blockers:
- Decisions made:
```
