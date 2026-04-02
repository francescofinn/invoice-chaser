# Invoice Chaser

Automated accounts receivable for freelancers and small business owners. Send invoices, collect payments via Stripe, and automatically chase overdue invoices with AI-generated follow-up emails.

## Features

- Create invoices with line items and assign to clients
- Client payment portal (no login) with Stripe card payments
- Automated follow-up emails at day 3, 7, and 14 after due date — AI-generated with escalating tone
- Dashboard with outstanding/overdue totals, cash flow forecast, and late payment risk indicators

## Prerequisites

- Python 3.11+
- Node 18+
- PostgreSQL 15+
- [Stripe CLI](https://stripe.com/docs/stripe-cli) (for local webhook forwarding)
- Stripe account (test mode is fine)
- [Resend](https://resend.com) account with a verified sending domain
- Anthropic API key

## Setup

### 1. Clone and configure environment

```bash
git clone <repo-url>
cd invoice-chaser
cp .env.example .env
# Edit .env and fill in all values
```

For the frontend, also create `frontend/.env`:
```
VITE_API_URL=http://localhost:8000
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_...
```

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create the database
createdb invoice_chaser

# Run migrations
alembic upgrade head

# Seed sample data
python seed.py

# Start the API server
uvicorn main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
# App available at http://localhost:5173
```

### 4. Stripe webhook forwarding (local development)

In a separate terminal:

```bash
stripe listen --forward-to localhost:8000/webhooks/stripe
```

Copy the webhook signing secret printed in the terminal output into `.env` as `STRIPE_WEBHOOK_SECRET`.

Test payments use card number `4242 4242 4242 4242` with any future expiry and any CVC.

### 5. Resend setup

Update the `from` address in `backend/services/email.py` to a domain you have verified in your Resend account. See [Resend domain setup](https://resend.com/docs/dashboard/domains/introduction).

## Project Structure

```
invoice-chaser/
├── backend/          # FastAPI API server
│   ├── routers/      # API route handlers
│   └── services/     # Stripe, Resend, Claude, APScheduler
└── frontend/         # React/Vite SPA
    └── src/
        ├── api/      # React Query hooks
        ├── pages/    # Route-level components
        └── components/
```

## Security Note

The admin UI (`/`, `/invoices`, etc.) has **no authentication**. Do not expose this application to the public internet without adding an auth layer (e.g., OAuth2, Clerk, Auth0). The client payment portal at `/pay/:token` uses an unguessable UUID token for access control.
