# Collections Operator Agent Context

## Purpose

This document is the implementation handoff context for any agent working on the AI Collections Operator feature.

Read this together with:

- [`docs/plan-ai-collections-operator.md`](./plan-ai-collections-operator.md)
- [`docs/plan-backend.md`](./plan-backend.md)

The operator plan is the source spec for the feature. This file explains the current project shape, what already exists, what is missing, and what constraints the implementer must preserve.

## Product snapshot

Invoice Chaser is an AR workflow app for solo businesses. Today it supports:

- Clerk-authenticated admin UI
- client and invoice management
- public payment links backed by Stripe PaymentIntents
- AI-generated overdue follow-up emails
- a dashboard summary with cash-flow forecast

The Collections Operator feature is the next layer: a dashboard agent that explains collection risk, recommends next actions, drafts outreach, classifies client replies, updates forecast expectations, and queues the next step.

## Current architecture

### Frontend

Stack:

- React + Vite
- React Router
- TanStack Query
- Clerk React SDK
- Tailwind

Important current surfaces:

- [`frontend/src/App.jsx`](../frontend/src/App.jsx)
  - Admin routes are already Clerk-gated in the frontend.
  - Public payment portal lives at `/pay/:token`.
- [`frontend/src/components/Layout.jsx`](../frontend/src/components/Layout.jsx)
  - Sidebar currently has `Dashboard` and `Invoices`.
- [`frontend/src/pages/Dashboard.jsx`](../frontend/src/pages/Dashboard.jsx)
  - Existing dashboard renders summary cards, forecast chart, and recent invoices.
  - The operator v1 should live here, not on a new top-level page.
- [`frontend/src/api/client.js`](../frontend/src/api/client.js)
  - Authenticated admin API calls already attach a Clerk bearer token.
  - Public payment calls use a separate unauthenticated client.
- [`frontend/src/api/dashboard.js`](../frontend/src/api/dashboard.js)
  - Existing dashboard summary query is already polling on a 60s interval.
- [`frontend/src/api/invoices.js`](../frontend/src/api/invoices.js)
  - Existing invoice queries and mutations should remain the base invoice workflow.

### Backend

Stack:

- FastAPI
- SQLAlchemy 2
- Alembic
- PostgreSQL / Neon target
- Stripe
- Resend
- Anthropic
- APScheduler

Important current surfaces:

- [`backend/main.py`](../backend/main.py)
  - App wiring and router registration already exist.
- [`backend/database.py`](../backend/database.py)
  - Central settings loader and DB session factory.
- [`backend/models.py`](../backend/models.py)
  - Current DB entities are `Client`, `Invoice`, `Payment`, and `EmailLog`.
- [`backend/schemas.py`](../backend/schemas.py)
  - Current response shapes already power the frontend.
- [`backend/routers/invoices.py`](../backend/routers/invoices.py)
  - Invoice CRUD, send flow, and public payment portal are implemented.
- [`backend/routers/dashboard.py`](../backend/routers/dashboard.py)
  - Current forecast is due-date based and unaware of commitments.
- [`backend/services/ai.py`](../backend/services/ai.py)
  - Current AI usage is limited to follow-up email generation.
- [`backend/services/scheduler.py`](../backend/services/scheduler.py)
  - Existing scheduler marks invoices overdue and sends automated follow-ups.

## Current state vs planned state

### Already implemented

- Invoice lifecycle:
  - `draft`
  - `sent`
  - `viewed`
  - `partially_paid`
  - `paid`
  - `overdue`
- Public payment token flow
- Stripe webhook payment reconciliation
- Dashboard summary and forecast
- Outbound email sending
- AI-generated follow-up emails
- Clerk-protected frontend admin routes

### Not yet implemented, but expected by the updated backend plan

- `backend/auth.py`
- backend Clerk JWT verification
- protected admin API routes using Clerk bearer auth
- Neon direct migration URL handling via `DIRECT_DATABASE_URL`

This means there is a real frontend/backend auth mismatch right now:

- the frontend already sends Clerk tokens
- the backend currently does not verify them

Any agent implementing the operator should be aware of that gap. The operator plan assumes admin endpoints are protected. If auth is not implemented first, new operator routes will still work locally but will not match the updated backend contract.

### Not yet implemented, and part of the operator feature

- operator-specific persistence
- operator-specific API routes
- operator-specific AI analysis/classification
- reply simulation workflow
- forecast override using commitments
- operator UI on the dashboard

## Non-negotiable project constraints

These behaviors already exist and must not be broken:

- Keep `Invoice.status` vocabulary exactly as it is.
- `Invoice.line_items` must remain JSON list-of-dicts.
- Invoice totals must continue using `Decimal(str(...))` logic.
- `GET /invoices/public/{token}` remains public and must be declared before `GET /invoices/{id}`.
- Stripe webhook verification must use the raw request body.
- Existing invoice CRUD and payment portal behavior must keep working unchanged.
- The dashboard must continue returning:
  - `total_outstanding`
  - `total_overdue`
  - `total_paid_this_month`
  - `invoice_count_by_status`
  - `cash_flow_forecast`

For operator v1 specifically:

- The operator is dashboard-first.
- The reply flow is simulated, not real email ingestion.
- Outbound send is real.
- Payment-plan replies update state and forecast only.
- The Stripe payment portal is not extended to installments in v1.

## Operator v1 product decisions already locked

These decisions are already made and should not be reopened during implementation:

- Primary surface: dashboard panel
- Build goal: balanced hackathon demo plus future-friendly backend
- Demo trigger: visible demo controls in the UI
- Send mode: real outbound send plus simulated inbound reply
- Reply ingestion: simulated flow for v1
- Payment-plan scope: state + forecast only
- Persistence strategy: durable operator state in new tables, not transient-only demo data

## What the operator implementation must add

The implementation agent should build exactly this new capability set:

- queue overdue and at-risk invoices in an operator worklist
- analyze a selected invoice and explain risk in plain English
- recommend a next best action
- generate a draft outreach message
- send that draft through the existing email system
- simulate a client reply from visible canned controls
- classify that reply into a structured workflow outcome
- create durable commitments such as promise-to-pay or payment-plan installments
- update the forecast to use commitments instead of only due dates
- queue the next operator follow-up date without auto-sending it

## Suggested implementation breakdown

### 1. Backend contract and persistence

Add new models and migration for:

- `CollectionCase`
- `CollectionCommitment`
- `CollectionActivity`

Add new Pydantic schemas for:

- operator queue item
- operator case detail
- analyze response
- send response
- simulate reply request/response
- commitment objects
- activity objects
- forecast delta objects

### 2. Backend service layer

Extend the AI layer with:

- `generate_operator_analysis(...)`
- `classify_operator_reply(...)`

Provide deterministic fallback parsing so the demo does not fail if Anthropic is unavailable.

### 3. Backend routes

Add a protected `/operator` router with:

- `GET /operator/cases`
- `POST /operator/cases/{invoice_id}/analyze`
- `POST /operator/cases/{invoice_id}/send`
- `POST /operator/cases/{invoice_id}/simulate-reply`

### 4. Forecast integration

Update dashboard forecasting rules so:

- active commitments override invoice due-date forecasting
- invoices without commitments continue using due date
- `total_outstanding` stays based on remaining balance, not commitment totals

### 5. Frontend operator UI

Embed the operator in the existing dashboard page with:

- prioritized queue
- selected account detail
- risk summary
- recommendation card
- editable draft area
- send action
- canned reply simulation controls
- commitment timeline
- activity timeline
- before/after forecast change display

## Demo scenario the implementation must support

The canonical stage demo is:

1. An invoice becomes overdue.
2. The dashboard shows it in the operator queue.
3. The user clicks `Analyze account`.
4. The app displays:
   - risk explanation
   - next best action
   - generated message draft
5. The user clicks `Send draft`.
6. The user clicks the canned reply:
   - `Can I pay half now and the rest Friday?`
7. The app classifies the reply as a payment-plan request.
8. The app creates two commitments.
9. The operator updates:
   - case status
   - next follow-up date
   - forecast preview
   - activity timeline

If the implementation cannot do this full sequence smoothly, it is not done.

## File map the implementation agent should care about

Most relevant current files:

- [`backend/models.py`](../backend/models.py)
- [`backend/schemas.py`](../backend/schemas.py)
- [`backend/routers/dashboard.py`](../backend/routers/dashboard.py)
- [`backend/routers/invoices.py`](../backend/routers/invoices.py)
- [`backend/services/ai.py`](../backend/services/ai.py)
- [`backend/services/email.py`](../backend/services/email.py)
- [`frontend/src/pages/Dashboard.jsx`](../frontend/src/pages/Dashboard.jsx)
- [`frontend/src/api/dashboard.js`](../frontend/src/api/dashboard.js)
- [`frontend/src/api/invoices.js`](../frontend/src/api/invoices.js)
- [`frontend/src/components/SummaryCards.jsx`](../frontend/src/components/SummaryCards.jsx)
- [`frontend/src/components/CashFlowChart.jsx`](../frontend/src/components/CashFlowChart.jsx)

Expected new files or modules:

- `backend/auth.py`
- `backend/routers/operator.py`
- `frontend/src/api/operator.js`
- one or more new dashboard/operator UI components
- a new Alembic migration

## Testing expectations

Backend tests should cover:

- operator analysis persistence
- operator send workflow
- deterministic fallback reply classification
- payment-plan commitment creation
- promise-to-pay commitment creation
- queue ordering
- forecast override behavior

Frontend tests or acceptance checks should cover:

- dashboard operator panel render
- analyze action
- send action
- simulate reply action
- in-place forecast delta update

Manual acceptance should confirm:

- the demo works from a fresh seeded dataset
- the operator flow is understandable without narration
- no existing invoice, dashboard, or payment behavior regresses

## Environment and setup notes

Root `.env` is expected.

Current relevant environment variables:

- `DATABASE_URL`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `RESEND_API_KEY`
- `ANTHROPIC_API_KEY`
- `CLERK_SECRET_KEY`
- `CLERK_JWKS_URL`
- `FRONTEND_URL`

Recommended additional env handling from the backend plan:

- `DIRECT_DATABASE_URL` for Alembic on Neon

## Known gotchas

- The frontend is already Clerk-aware; the backend is not yet enforcing Clerk auth.
- Current dashboard data shape does not include operator-specific data.
- Current forecasting logic is invoice due-date based and must be carefully extended, not replaced blindly.
- Existing automated follow-up scheduler uses `EmailLog`; operator activity should use its own timeline model.
- Existing test setup still includes a generated SQLite artifact in `backend/tests/test.sqlite3`; do not rely on repo-tracked test DB files for new work.

## Definition of done

An implementation agent is done when:

- the operator queue exists on the dashboard
- analysis, send, and simulated reply flows are fully wired
- commitments are persisted
- forecast changes reflect commitments
- the canned payment-plan demo works end-to-end
- the feature is covered by backend tests and does not break existing flows
