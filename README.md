# Invoice Chaser

Automated accounts receivable for freelancers and small business owners. Send invoices, collect payments via Stripe, and automatically chase overdue invoices with AI-generated follow-up emails.

## Features

- Create invoices with line items and assign to clients
- Client payment portal (no login) with Stripe card payments
- Automated follow-up emails at day 3, 7, and 14 after due date — AI-generated with escalating tone
- Dashboard with outstanding/overdue totals, cash flow forecast, and late payment risk indicators
- Admin UI protected by Clerk authentication

## Prerequisites

- Python 3.11+
- Node 18+
- [Stripe CLI](https://stripe.com/docs/stripe-cli) (for local webhook forwarding)
- Accounts needed: [Neon](https://neon.tech) · [Stripe](https://stripe.com) · [Resend](https://resend.com) · [Clerk](https://clerk.com) · [Anthropic](https://console.anthropic.com)

## Setup

### 1. Clone and configure environment

```bash
git clone <repo-url>
cd invoice-chaser
cp .env.example .env
# Edit .env and fill in all values (see comments in .env.example)
```

**Frontend env** — create `frontend/.env`:
```
VITE_API_URL=http://localhost:8000
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_...
VITE_CLERK_PUBLISHABLE_KEY=pk_test_...
```

### 2. Neon database

1. Create a project at [console.neon.tech](https://console.neon.tech)
2. Copy the **pooled** connection string → paste as `DATABASE_URL` in `.env`
3. For Alembic migrations, also set `DIRECT_DATABASE_URL` to the **direct** (non-pooled) connection string

### 3. Clerk auth

1. Create an application at [dashboard.clerk.com](https://dashboard.clerk.com)
2. From **API Keys**: copy **Publishable key** → `VITE_CLERK_PUBLISHABLE_KEY` in `frontend/.env`
3. From **API Keys**: copy **Secret key** → `CLERK_SECRET_KEY` in `.env`
4. From **API Keys**: find your **Clerk domain** (e.g. `your-app.clerk.accounts.dev`)
5. Set `CLERK_JWKS_URL=https://your-app.clerk.accounts.dev/.well-known/jwks.json` in `.env`
6. In Clerk Dashboard → **Paths**, set the sign-in URL to `/sign-in`

### 4. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run migrations (uses DIRECT_DATABASE_URL if set, else DATABASE_URL)
alembic upgrade head

# Seed sample data
python seed.py

# Start the API server
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 5. Frontend

```bash
cd frontend
npm install
npm run dev
# App available at http://localhost:5173
```

### 6. Stripe webhook forwarding (local development)

In a separate terminal:

```bash
stripe listen --forward-to localhost:8000/webhooks/stripe
```

Copy the webhook signing secret → `STRIPE_WEBHOOK_SECRET` in `.env`.

Test payments: card `4242 4242 4242 4242`, any future expiry, any CVC.

### 7. Resend setup

Update the `from` address in `backend/services/email.py` to a domain verified in your Resend account. See [Resend domain setup](https://resend.com/docs/dashboard/domains/introduction).

## Project Structure

```
invoice-chaser/
├── backend/
│   ├── auth.py           # Clerk JWT verification (FastAPI dependency)
│   ├── routers/          # API route handlers
│   └── services/         # Stripe, Resend, Claude, APScheduler
├── frontend/
│   └── src/
│       ├── api/          # React Query hooks (auth-aware axios client)
│       ├── pages/        # Route-level components
│       └── components/
└── docs/
    ├── plan-backend.md   # Backend implementation guide
    └── plan-frontend.md  # Frontend implementation guide
```

## Auth model

- Admin UI (`/`, `/invoices`, etc.) requires Clerk sign-in → redirects to `/sign-in` if not authenticated
- Every API request from the frontend sends a `Bearer <clerk-jwt>` header
- Backend verifies the JWT against Clerk's JWKS endpoint (`backend/auth.py`)
- Client payment portal at `/pay/:token` is **public** — no login required, uses an unguessable UUID token
