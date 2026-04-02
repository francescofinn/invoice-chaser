# AI Collections Operator Implementation Plan

## Summary
- Build a dashboard-first AI Collections Operator that works as a strong hackathon demo and a clean foundation for the real product.
- Use real outbound email, visible demo controls, and simulated inbound replies so the stage flow is reliable.
- Keep the existing invoice lifecycle unchanged; store operator workflow in new collections-specific state.
- Treat payment-plan replies as state + forecast updates only in v1. Do not change the Stripe payment portal yet.

## Key Changes

### 1. Domain and persistence
- Add a 1:1 `CollectionCase` record per invoice with these fields: `invoice_id`, `status`, `risk_level`, `risk_summary`, `next_action_key`, `next_action_label`, `next_action_reason`, `draft_subject`, `draft_body`, `last_client_reply`, `last_reply_classification`, `last_contacted_at`, `queued_follow_up_date`, `last_analyzed_at`, `updated_at`.
- Add `CollectionCommitment` records for forecast-driving promises: `invoice_id`, `commitment_type`, `due_date`, `amount`, `status`, `source`, `created_at`.
- Add `CollectionActivity` records for the operator timeline: `invoice_id`, `activity_type`, `title`, `body`, `payload_json`, `created_at`.
- Preserve the current `Invoice.status` vocabulary exactly. Operator workflow state lives in `CollectionCase.status`, not `Invoice.status`.
- Use these `CollectionCase.status` values: `needs_analysis`, `action_ready`, `awaiting_client`, `promise_to_pay`, `payment_plan`, `needs_human_review`, `resolved`.
- Use these reply classifications: `promise_to_pay`, `payment_plan_request`, `paid_elsewhere`, `dispute`, `question`, `unknown`.
- Use these commitment types: `promise_to_pay`, `payment_plan_installment`.
- Add an Alembic migration for the three new tables.

### 2. Backend operator flow
- Add a new protected admin router for operator actions.
- Add `GET /operator/cases` to return the dashboard queue for invoices in `sent`, `viewed`, `partially_paid`, or `overdue`.
- Order the queue by: overdue first, `risk_level` high > medium > low, larger remaining balance first, then oldest `last_contacted_at`.
- Add `POST /operator/cases/{invoice_id}/analyze` to generate and persist:
  - plain-English risk explanation
  - next best action
  - action rationale
  - draft subject/body
  - `CollectionCase.status = action_ready`
- Add `POST /operator/cases/{invoice_id}/send` to send the current draft through the existing email service, set `last_contacted_at`, move the case to `awaiting_client`, and append a `CollectionActivity` event. Do not overload `EmailLog` for operator-only sends.
- Add `POST /operator/cases/{invoice_id}/simulate-reply` with body `{ "reply_text": string }` to:
  - persist the simulated inbound message as `CollectionActivity`
  - classify the reply with AI plus deterministic fallback heuristics
  - update `CollectionCase`
  - replace any active commitments for that invoice with the newly interpreted commitments
  - return the updated case plus a forecast delta payload for the selected invoice
- Use deterministic fallback rules so the demo still works if Anthropic fails:
  - `"half"` + future day/date => `payment_plan_request` with two commitments: 50% due today, 50% due on the parsed future date
  - future day/date without split language => `promise_to_pay` with one commitment
  - `"already paid"` => `paid_elsewhere`
  - `"wrong invoice"`, `"dispute"`, `"issue"` => `needs_human_review`
  - anything else => `unknown`
- Queue logic:
  - `promise_to_pay` => `queued_follow_up_date = promised_date + 1 day`
  - `payment_plan` => `queued_follow_up_date = earliest active commitment due_date + 1 day`
  - `paid_elsewhere` => no queued follow-up, case becomes `resolved`
  - `needs_human_review` or `unknown` => no automated queue
- Do not auto-send queued operator follow-ups in v1. Persist and surface the next step on the dashboard.

### 3. AI and forecasting behavior
- Extend the AI service with two explicit functions:
  - `generate_operator_analysis(invoice_context, client_context, payment_context)`
  - `classify_operator_reply(invoice_context, reply_text)`
- Analysis output must include: `risk_level`, `risk_summary`, `next_action_key`, `next_action_label`, `next_action_reason`, `draft_subject`, `draft_body`.
- Reply classification output must include: `classification`, `rationale`, `commitments`, `queued_follow_up_date`, `next_case_status`.
- Update dashboard forecasting so active commitments override due-date forecasting:
  - if an invoice has active commitments, forecast those commitment dates/amounts
  - otherwise forecast the remaining balance on the invoice due date
- Keep `total_outstanding` based on remaining unpaid balance, not raw commitment totals.
- Return a per-invoice forecast delta after simulated reply processing so the UI can show the “before vs after” change during the demo.

### 4. Frontend and demo UX
- Add a dedicated operator data layer and render it inside the existing dashboard page rather than a new route.
- Add a dashboard operator panel with:
  - prioritized queue list
  - selected account detail view
  - risk summary card
  - next-best-action card
  - editable draft composer
  - commitments/forecast preview
  - recent activity timeline
- Keep the demo controls visible in v1:
  - `Analyze account`
  - `Send draft`
  - `Simulate client reply`
- Ship three canned reply shortcuts, with `"Can I pay half now and the rest Friday?"` as the primary demo action.
- After simulated reply, update the panel immediately to show:
  - classification
  - new case status
  - commitment schedule
  - queued follow-up date
  - forecast delta
- Keep the existing invoice detail page unchanged except for an optional “Open in Operator” link if helpful.

## Public APIs / Interfaces
- New backend router: `/operator`
- New response shape for operator queue items:
  - `invoice`
  - `client`
  - `remaining_amount`
  - `case`
  - `commitments`
  - `recent_activity`
- `POST /operator/cases/{invoice_id}/simulate-reply` response must include:
  - `case`
  - `commitments`
  - `forecast_before`
  - `forecast_after`
- Add a frontend operator API module with hooks for:
  - queue fetch
  - analyze
  - send
  - simulate reply

## Test Plan
- Backend:
  - analyzing an overdue invoice creates or updates `CollectionCase`
  - sending a draft creates an outbound activity record and moves status to `awaiting_client`
  - simulating `"Can I pay half now and the rest Friday?"` classifies as `payment_plan_request`, creates two commitments, sets `CollectionCase.status = payment_plan`, and sets the correct queued follow-up date
  - simulating a simple promise-to-pay creates one commitment and updates the forecast
  - forecast uses active commitments instead of raw due date when commitments exist
  - Anthropic failure falls back to deterministic parsing without breaking the demo
  - queue ordering matches overdue/risk/balance/contact rules
- Frontend:
  - dashboard shows operator queue and selected case
  - analyze action renders risk summary, recommendation, and draft
  - send action updates the case state and timeline
  - simulated reply updates classification, commitments, and forecast delta in place
  - canned reply controls are visible and stage-friendly
- Demo acceptance:
  - one overdue invoice can be analyzed from the dashboard
  - the operator explains risk in plain English
  - the operator proposes and sends a draft
  - the canned “half now and the rest Friday” reply updates the case to a payment-plan state
  - the cash forecast visibly changes without reloading the app

## Assumptions and defaults
- This plan is dashboard-first and does not add a standalone operator page.
- Inbound reply handling is simulated only in v1; no real email ingestion or webhook parsing is in scope.
- Partial payments are not added to the Stripe portal in v1. The operator only persists commitments and forecast changes.
- Operator endpoints should use the same admin auth boundary as the rest of the admin API once Clerk auth lands; auth expansion itself is not part of this feature plan.
