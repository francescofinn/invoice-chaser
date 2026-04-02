# Invoice Chaser — Backend Implementation Plan

## Ownership
This doc covers everything in `backend/`. The frontend developer works in `frontend/` in parallel using the shared API contract below.

---

## Stack
- Python 3.11+, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL (Neon)
- Stripe SDK, Resend SDK, Anthropic SDK, APScheduler
- Clerk (JWT verification via python-jose)

---

## Project Structure to Create

```
backend/
├── main.py                  # FastAPI app factory, CORS, lifespan
├── database.py              # SQLAlchemy engine, SessionLocal, Settings
├── models.py                # ORM models
├── schemas.py               # Pydantic v2 schemas
├── requirements.txt
├── seed.py
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 0001_initial.py
├── auth.py                  # Clerk JWT verification dependency
├── routers/
│   ├── __init__.py
│   ├── clients.py
│   ├── invoices.py
│   ├── dashboard.py
│   └── webhooks.py
└── services/
    ├── __init__.py
    ├── email.py
    ├── ai.py
    └── scheduler.py
```

---

## Environment Variables

Create `.env` from `.env.example` in the repo root:

```
# Neon — use the "pooled" connection string (Session mode)
DATABASE_URL=postgresql+psycopg2://user:password@ep-xxx.us-east-1.aws.neon.tech/neondb?sslmode=require

STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
RESEND_API_KEY=re_...
ANTHROPIC_API_KEY=sk-ant-...

# Clerk
CLERK_SECRET_KEY=sk_test_...
CLERK_JWKS_URL=https://your-clerk-domain.clerk.accounts.dev/.well-known/jwks.json

FRONTEND_URL=http://localhost:5173
```

**Neon note**: Use the *pooled* connection string (Session mode) for the app. If you run Alembic migrations, use the *direct* (unpooled) URL to avoid prepared statement conflicts — set it as `DIRECT_DATABASE_URL` and use it only in `alembic/env.py`.

---

## `requirements.txt`

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy==2.0.30
alembic==1.13.1
psycopg2-binary==2.9.9
pydantic==2.7.1
pydantic-settings==2.2.1
stripe==9.9.0
resend==2.0.0
anthropic==0.26.0
apscheduler==3.10.4
python-dotenv==1.0.1
httpx==0.27.0
python-jose[cryptography]==3.3.0
cachetools==5.3.3
```

---

## `auth.py` — Clerk JWT Verification

FastAPI dependency that verifies Clerk JWTs on every protected request. JWKS is cached for 1 hour to avoid fetching on every request.

**Which endpoints are protected**: all admin routers (`clients`, `invoices`, `dashboard`).
**Which stay public**: `GET /invoices/public/{token}` and `POST /webhooks/stripe`.

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx
from cachetools import TTLCache
from database import settings

security = HTTPBearer()
_jwks_cache: TTLCache = TTLCache(maxsize=1, ttl=3600)  # cache for 1 hour

def _get_jwks() -> dict:
    if "jwks" in _jwks_cache:
        return _jwks_cache["jwks"]
    response = httpx.get(settings.clerk_jwks_url, timeout=10)
    response.raise_for_status()
    jwks = response.json()
    _jwks_cache["jwks"] = jwks
    return jwks

async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Returns the decoded JWT claims. Raises 401 on any failure."""
    token = credentials.credentials
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")

        jwks = _get_jwks()
        signing_key = next(
            (k for k in jwks.get("keys", []) if k.get("kid") == kid), None
        )
        if not signing_key:
            raise HTTPException(status_code=401, detail="Signing key not found")

        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            options={"verify_aud": False},  # Clerk doesn't set aud by default
        )
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
```

**Add to `Settings` in `database.py`**:
```python
clerk_secret_key: str
clerk_jwks_url: str
```

**Apply to routers** — add `Depends(require_auth)` to each admin router. Example:
```python
from auth import require_auth
from fastapi import Depends

router = APIRouter()

@router.get("/", response_model=List[ClientResponse])
def list_clients(db: Session = Depends(get_db), _=Depends(require_auth)):
    ...
```

The `_=Depends(require_auth)` pattern discards the claims (you don't need to use the user ID for single-user apps). If you later add multi-tenancy, replace `_` with `claims` and filter queries by `claims["sub"]`.

---

## `database.py`

Use `pydantic-settings` to load all env vars from `.env`. Single source of truth — all routers and services import `settings` from here.

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    stripe_secret_key: str
    stripe_webhook_secret: str
    resend_api_key: str
    anthropic_api_key: str
    frontend_url: str = "http://localhost:5173"

    class Config:
        env_file = ".env"

settings = Settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## `models.py`

Four ORM models. Key decisions:
- `Invoice.line_items` → `JSON` column (maps to `jsonb` in PostgreSQL), stored as list of dicts
- `Invoice.token` → `UUID` column with `default=uuid4`, used in the public payment URL
- `Invoice.status` → plain `String` column (not PostgreSQL enum, avoids migration pain)
- `Invoice.stripe_payment_intent_id` → `String`, nullable — stored after first PI creation to support idempotency on the public portal
- `Payment.amount` → `Numeric(10, 2)` — never float for money

```python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey, JSON, Text, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    company = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    invoices = relationship("Invoice", back_populates="client")

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    invoice_number = Column(String, unique=True, nullable=False)
    issue_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(String, default="draft")  # draft/sent/viewed/partially_paid/paid/overdue
    token = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    line_items = Column(JSON, default=list)
    notes = Column(Text)
    stripe_payment_intent_id = Column(String, nullable=True)
    client = relationship("Client", back_populates="invoices")
    payments = relationship("Payment", back_populates="invoice")
    email_logs = relationship("EmailLog", back_populates="invoice")

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    stripe_payment_intent_id = Column(String, unique=True)
    paid_at = Column(DateTime, default=datetime.utcnow)
    invoice = relationship("Invoice", back_populates="payments")

class EmailLog(Base):
    __tablename__ = "email_logs"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    subject = Column(String)
    body = Column(Text)
    follow_up_day = Column(Integer)  # 0 = initial send, 3/7/14 = follow-up
    invoice = relationship("Invoice", back_populates="email_logs")
```

---

## `schemas.py`

Pydantic v2. Use `model_config = ConfigDict(from_attributes=True)` (replaces `orm_mode`). `LineItem` is a nested model used within Invoice JSON — not a DB model.

Key schema: `InvoiceResponse` has a `@computed_field` for `total` that sums `line_items` in Python (since total is not stored in the DB).

```python
from pydantic import BaseModel, ConfigDict, computed_field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
import uuid

class LineItem(BaseModel):
    description: str
    quantity: Decimal
    unit_price: Decimal

class ClientCreate(BaseModel):
    name: str
    email: str
    company: Optional[str] = None

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None

class ClientResponse(ClientCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime

class InvoiceCreate(BaseModel):
    client_id: int
    invoice_number: str
    issue_date: date
    due_date: date
    line_items: List[LineItem] = []
    notes: Optional[str] = None

class InvoiceUpdate(BaseModel):
    due_date: Optional[date] = None
    status: Optional[str] = None
    line_items: Optional[List[LineItem]] = None
    notes: Optional[str] = None

class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    client_id: int
    invoice_number: str
    issue_date: date
    due_date: date
    status: str
    token: uuid.UUID
    line_items: List[dict]
    notes: Optional[str] = None
    client: ClientResponse

    @computed_field
    @property
    def total(self) -> Decimal:
        return sum(
            Decimal(str(item["quantity"])) * Decimal(str(item["unit_price"]))
            for item in (self.line_items or [])
        )

class PublicInvoiceResponse(InvoiceResponse):
    stripe_client_secret: str  # added for payment portal

class DashboardSummary(BaseModel):
    total_outstanding: Decimal
    total_overdue: Decimal
    total_paid_this_month: Decimal
    invoice_count_by_status: dict
    cash_flow_forecast: List[dict]  # [{date, expected_amount, invoice_ids}]
```

---

## `routers/clients.py`

Standard CRUD. 404 on missing client.

```python
GET  /clients          → list all clients
POST /clients          → create (ClientCreate → ClientResponse)
GET  /clients/{id}     → get one (404 if missing)
PUT  /clients/{id}     → update (ClientUpdate → ClientResponse)
DELETE /clients/{id}   → delete (also check for associated invoices — return 409 if any exist)
```

---

## `routers/invoices.py`

CRUD plus two special endpoints:

**Standard CRUD:**
```
GET    /invoices                → list with optional ?status= filter
POST   /invoices                → create (InvoiceCreate → InvoiceResponse)
GET    /invoices/{id}           → get one with client relationship loaded
PUT    /invoices/{id}           → update (InvoiceUpdate → InvoiceResponse)
DELETE /invoices/{id}           → delete (only draft status)
```

**Special endpoints:**

`POST /invoices/{id}/send`
1. Fetch invoice + client, verify status is `draft`
2. Compute total from `line_items`
3. Create Stripe PaymentIntent: `stripe.PaymentIntent.create(amount=int(total*100), currency="usd", metadata={"invoice_id": str(invoice.id)})`
4. Store `stripe_payment_intent_id` on invoice
5. Set `invoice.status = "sent"`
6. Build `payment_link = f"{settings.frontend_url}/pay/{invoice.token}"`
7. Send initial invoice email via `services/email.py`
8. Create `EmailLog(follow_up_day=0)` record
9. Commit and return updated `InvoiceResponse`

`GET /invoices/public/{token}` — **no auth required**
1. Look up invoice by `token` (UUID)
2. If `invoice.stripe_payment_intent_id` is set: call `stripe.PaymentIntent.retrieve(id)` — if status is not `cancelled`, use existing `client_secret`
3. Otherwise: create new PaymentIntent, store ID on invoice
4. Return `PublicInvoiceResponse` (includes `stripe_client_secret`)
5. If invoice status is `sent`, update to `viewed`

Note: This endpoint must be registered BEFORE `GET /invoices/{id}` in the router to avoid FastAPI routing the string `"public"` as an integer ID parameter.

---

## `routers/webhooks.py`

```python
POST /webhooks/stripe

1. raw_body = await request.body()  # MUST read raw before any JSON parsing
2. sig = request.headers["stripe-signature"]
3. event = stripe.Webhook.construct_event(raw_body, sig, settings.stripe_webhook_secret)
   → 400 on SignatureVerificationError

4. if event["type"] == "payment_intent.succeeded":
   pi = event["data"]["object"]
   invoice_id = int(pi["metadata"]["invoice_id"])
   amount_paid = Decimal(pi["amount_received"]) / 100

   # Idempotency: skip if Payment record already exists for this PI
   existing = db.query(Payment).filter_by(stripe_payment_intent_id=pi["id"]).first()
   if not existing:
       db.add(Payment(invoice_id=invoice_id, amount=amount_paid, stripe_payment_intent_id=pi["id"]))

   # Recalculate total paid and update status
   total_paid = sum(p.amount for p in invoice.payments) + (amount_paid if not existing else 0)
   invoice.status = "paid" if total_paid >= invoice_total else "partially_paid"
   db.commit()

5. return {"status": "ok"}
```

---

## `routers/dashboard.py`

`GET /dashboard/summary` → `DashboardSummary`

- `total_outstanding`: sum of invoice totals where status in (`sent`, `viewed`, `partially_paid`, `overdue`)
- `total_overdue`: sum of above where `due_date < today`
- `total_paid_this_month`: `SUM(payments.amount)` where `paid_at >= first of current month`
- `invoice_count_by_status`: `GROUP BY status` count
- `cash_flow_forecast`: unpaid invoices (`sent`/`viewed`/`partially_paid`) with `due_date` between today and today+90, grouped by date → `[{date, expected_amount, invoice_ids}]`

Note: `total` per invoice must be computed in Python since it's derived from JSON `line_items` — not a SQL-aggregatable column.

---

## `services/email.py`

Resend SDK wrapper. The `from` address must be a verified domain in your Resend account.

```python
import resend
from database import settings

resend.api_key = settings.resend_api_key

def send_invoice_email(to_email: str, subject: str, body: str, payment_link: str) -> str:
    """Returns Resend message ID."""
    html = body.replace("\n", "<br>")
    params = {
        "from": "Invoice Chaser <invoices@yourdomain.com>",  # update domain
        "to": [to_email],
        "subject": subject,
        "html": f"{html}<br><br><a href='{payment_link}'>Pay Now →</a>",
    }
    response = resend.Emails.send(params)
    return response["id"]
```

---

## `services/ai.py`

Anthropic Claude wrapper for follow-up email generation. Uses `claude-sonnet-4-6` (latest).

```python
import anthropic, json, logging
from database import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
logger = logging.getLogger(__name__)

TONE_MAP = {
    3:  "friendly and gentle — assume the client may have simply forgotten",
    7:  "professional and direct — politely but clearly state the invoice is overdue",
    14: "firm and urgent — make clear that further action may be taken if not resolved promptly",
}

FALLBACK = {
    3:  {"subject": "Friendly reminder: Invoice {num} due", "body": "Hi {name},\n\nJust a quick reminder that invoice {num} for ${amount} was due on {due_date}. Please pay at: {link}"},
    7:  {"subject": "Invoice {num} is overdue", "body": "Hi {name},\n\nInvoice {num} for ${amount} (due {due_date}) remains unpaid. Please settle at: {link}"},
    14: {"subject": "Urgent: Invoice {num} requires immediate attention", "body": "Hi {name},\n\nInvoice {num} for ${amount} is now 14 days overdue. Immediate payment is required: {link}"},
}

def generate_follow_up_email(client_name, invoice_number, amount_due, due_date, days_overdue, payment_link, follow_up_day) -> dict:
    tone = TONE_MAP.get(follow_up_day, TONE_MAP[3])
    prompt = f"""Write a payment follow-up email for a small business owner.
Client: {client_name} | Invoice: {invoice_number} | Amount: ${amount_due} | Due: {due_date} | Days overdue: {days_overdue}
Payment link: {payment_link}
Tone: {tone}
Keep it 3-5 sentences. Return ONLY valid JSON with keys "subject" and "body". No other text."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(message.content[0].text)
    except Exception as e:
        logger.error(f"AI generation failed: {e}")
        tmpl = FALLBACK.get(follow_up_day, FALLBACK[3])
        return {
            "subject": tmpl["subject"].format(num=invoice_number),
            "body": tmpl["body"].format(name=client_name, num=invoice_number, amount=amount_due, due_date=due_date, link=payment_link),
        }
```

---

## `services/scheduler.py`

`BackgroundScheduler` (thread-based — all DB access uses synchronous `SessionLocal()`).

Two daily jobs:
1. **Mark overdue** (midnight): set `status = "overdue"` for `sent`/`viewed` invoices where `due_date < today`
2. **Send follow-ups** (9am): for each overdue invoice, check if `days_overdue` is exactly 3, 7, or 14; if no `EmailLog` exists for that `follow_up_day`, generate AI email, insert `EmailLog` row, then send via Resend. Roll back if send fails.

Idempotency pattern for follow-ups:
```python
# Insert BEFORE sending to prevent duplicates on retry
log = EmailLog(invoice_id=invoice.id, subject=..., body=..., follow_up_day=days_overdue)
db.add(log)
db.flush()  # get ID without committing
send_invoice_email(...)
db.commit()
# On exception: db.rollback() — log row is removed, job will retry next run
```

Scheduler wired into `main.py` lifespan:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()
```

---

## `main.py`

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import settings
from services.scheduler import start_scheduler, stop_scheduler
from routers import clients, invoices, dashboard, webhooks

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()

app = FastAPI(title="Invoice Chaser API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clients.router, prefix="/clients", tags=["clients"])
app.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
```

---

## Alembic Setup

```bash
cd backend
alembic init alembic
```

Edit `alembic/env.py`:
- Import `Base` from `models` and `settings` from `database`
- Set `target_metadata = Base.metadata`
- Override `sqlalchemy.url` with `settings.database_url`

```bash
alembic revision --autogenerate -m "initial tables"
alembic upgrade head
```

---

## `seed.py`

```python
"""Run: python seed.py from backend/ directory"""
from database import SessionLocal, engine, Base
from models import Client, Invoice
from datetime import date, timedelta

Base.metadata.create_all(bind=engine)
db = SessionLocal()

clients = [
    Client(name="Alice Johnson", email="alice@example.com", company="Johnson Design"),
    Client(name="Bob Martinez", email="bob@example.com", company="Martinez Consulting"),
    Client(name="Carol White", email="carol@example.com", company="White Media"),
]
db.add_all(clients)
db.flush()

today = date.today()
invoices = [
    Invoice(
        client_id=clients[0].id, invoice_number="INV-001",
        issue_date=today - timedelta(days=30), due_date=today - timedelta(days=10),
        status="overdue",
        line_items=[
            {"description": "Brand Strategy", "quantity": 1, "unit_price": 2500.00},
            {"description": "Logo Design", "quantity": 1, "unit_price": 750.00},
        ],
    ),
    Invoice(
        client_id=clients[1].id, invoice_number="INV-002",
        issue_date=today - timedelta(days=10), due_date=today + timedelta(days=20),
        status="sent",
        line_items=[{"description": "Consulting Hours", "quantity": 8, "unit_price": 150.00}],
    ),
    Invoice(
        client_id=clients[2].id, invoice_number="INV-003",
        issue_date=today, due_date=today + timedelta(days=30),
        status="draft",
        line_items=[{"description": "Website Copy", "quantity": 3, "unit_price": 400.00}],
    ),
]
db.add_all(invoices)
db.commit()
print("Seeded 3 clients and 3 invoices.")
db.close()
```

---

## API Contract for Frontend Developer

The frontend expects these response shapes. Do not change field names without coordinating.

### `GET /invoices` and `GET /invoices/{id}`
```json
{
  "id": 1,
  "client_id": 1,
  "invoice_number": "INV-001",
  "issue_date": "2026-03-03",
  "due_date": "2026-03-23",
  "status": "overdue",
  "token": "550e8400-e29b-41d4-a716-446655440000",
  "line_items": [{"description": "...", "quantity": "1", "unit_price": "2500.00"}],
  "notes": null,
  "total": "2500.00",
  "client": {"id": 1, "name": "Alice Johnson", "email": "alice@example.com", "company": "...", "created_at": "..."}
}
```

### `GET /invoices/public/{token}`
Same as above plus:
```json
{
  "stripe_client_secret": "pi_xxx_secret_yyy"
}
```

### `GET /dashboard/summary`
```json
{
  "total_outstanding": "4700.00",
  "total_overdue": "3250.00",
  "total_paid_this_month": "1200.00",
  "invoice_count_by_status": {"draft": 1, "sent": 1, "overdue": 1},
  "cash_flow_forecast": [
    {"date": "2026-04-22", "expected_amount": 1200.0, "invoice_ids": [2]}
  ]
}
```

---

## Local Development

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env  # fill in your keys
createdb invoice_chaser
alembic upgrade head
python seed.py
uvicorn main:app --reload --port 8000
```

Stripe webhook forwarding (separate terminal):
```bash
stripe listen --forward-to localhost:8000/webhooks/stripe
# Copy the webhook signing secret printed here into .env STRIPE_WEBHOOK_SECRET
```

API docs available at: `http://localhost:8000/docs`

---

## Notes

- **Auth**: Admin endpoints have no authentication. Do not expose to public internet without adding an auth layer.
- **Resend**: Update the `from` address in `services/email.py` to a domain you've verified in Resend.
- **Decimal precision**: Always use `Decimal(str(value))` when reading from `line_items` JSON to avoid float rounding errors.
- **Scheduler + async**: APScheduler `BackgroundScheduler` runs in a thread pool. All DB access in scheduler jobs uses synchronous `SessionLocal()`, not async sessions.
