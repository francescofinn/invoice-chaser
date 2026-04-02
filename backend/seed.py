"""Run from the backend directory with: python seed.py"""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

from database import Base, SessionLocal, engine
from models import Client, EmailLog, Invoice, Payment

Base.metadata.create_all(bind=engine)

TODAY = date.today()


def d(days: int) -> date:
    return TODAY + timedelta(days=days)


def paid_at(days_ago: int) -> datetime:
    return datetime.utcnow() - timedelta(days=days_ago)


def main() -> None:
    db = SessionLocal()
    try:
        if db.query(Client).count() > 0:
            print("Seed data already exists. Skipping.")
            return

        # ------------------------------------------------------------------
        # Clients — mix of industries to make the demo feel real
        # ------------------------------------------------------------------
        clients = [
            Client(name="Sarah Chen",        email="sarah@novabranding.co",     company="Nova Branding Co."),
            Client(name="James Okafor",       email="james@pillardigital.io",    company="Pillar Digital"),
            Client(name="Mia Rossi",          email="mia@crescentmedia.com",     company="Crescent Media"),
            Client(name="Luca Ferreira",      email="luca@axisweb.dev",          company="Axis Web Dev"),
            Client(name="Priya Nair",         email="priya@lumensocial.co",      company="Lumen Social"),
            Client(name="Tom Gallagher",      email="tom@ironroofing.net",       company="Iron Roofing Ltd."),
            Client(name="Yuki Tanaka",        email="yuki@studiokinetic.jp",     company="Studio Kinetic"),
            Client(name="Elena Vasquez",      email="elena@blueprintarch.com",   company="Blueprint Architecture"),
            Client(name="Marcus Webb",        email="marcus@webblegal.com",      company="Webb Legal Group"),
            Client(name="Claudia Bauer",      email="claudia@freshcopy.de",      company="Fresh Copy GmbH"),
        ]
        db.add_all(clients)
        db.flush()

        c = clients  # shorthand

        invoices_data = [
            # ---- PAID (recent — contributes to "paid this month") ----
            dict(client=c[0], num="INV-001", issue=d(-35), due=d(-14), status="paid",
                 items=[{"description": "Brand Identity System", "quantity": "1", "unit_price": "4800.00"},
                        {"description": "Style Guide PDF", "quantity": "1", "unit_price": "600.00"}]),
            dict(client=c[1], num="INV-002", issue=d(-28), due=d(-7), status="paid",
                 items=[{"description": "SEO Audit", "quantity": "1", "unit_price": "1200.00"},
                        {"description": "Keyword Research Report", "quantity": "1", "unit_price": "450.00"}]),
            dict(client=c[3], num="INV-003", issue=d(-20), due=d(-5), status="paid",
                 items=[{"description": "Landing Page Development", "quantity": "1", "unit_price": "2200.00"},
                        {"description": "Mobile Optimisation", "quantity": "1", "unit_price": "400.00"}]),
            dict(client=c[6], num="INV-004", issue=d(-30), due=d(-10), status="paid",
                 items=[{"description": "Motion Graphics Package", "quantity": "3", "unit_price": "950.00"}]),
            dict(client=c[8], num="INV-005", issue=d(-15), due=d(-3), status="paid",
                 items=[{"description": "Contract Review", "quantity": "4", "unit_price": "350.00"},
                        {"description": "Legal Consultation", "quantity": "2", "unit_price": "500.00"}]),

            # ---- OVERDUE ----
            dict(client=c[2], num="INV-006", issue=d(-45), due=d(-15), status="overdue",
                 items=[{"description": "Social Media Campaign", "quantity": "1", "unit_price": "3200.00"},
                        {"description": "Ad Creative (5 variants)", "quantity": "5", "unit_price": "280.00"}]),
            dict(client=c[4], num="INV-007", issue=d(-40), due=d(-14), status="overdue",
                 items=[{"description": "Instagram Content (Month 1)", "quantity": "1", "unit_price": "1800.00"}]),
            dict(client=c[5], num="INV-008", issue=d(-50), due=d(-20), status="overdue",
                 items=[{"description": "Roof Inspection Report", "quantity": "1", "unit_price": "750.00"},
                        {"description": "Emergency Repair Assessment", "quantity": "1", "unit_price": "2400.00"}]),
            dict(client=c[9], num="INV-009", issue=d(-35), due=d(-8), status="overdue",
                 items=[{"description": "Copywriting — Homepage", "quantity": "1", "unit_price": "1100.00"},
                        {"description": "Blog Posts (x4)", "quantity": "4", "unit_price": "320.00"}]),

            # ---- SENT / VIEWED (due in the next 90 days — feeds the forecast chart) ----
            dict(client=c[7], num="INV-010", issue=d(-10), due=d(5),  status="sent",
                 items=[{"description": "Architectural Visualisation", "quantity": "2", "unit_price": "2700.00"}]),
            dict(client=c[0], num="INV-011", issue=d(-8),  due=d(8),  status="viewed",
                 items=[{"description": "Brand Refresh Consultation", "quantity": "3", "unit_price": "600.00"},
                        {"description": "Updated Logo Files", "quantity": "1", "unit_price": "400.00"}]),
            dict(client=c[1], num="INV-012", issue=d(-5),  due=d(12), status="sent",
                 items=[{"description": "PPC Campaign Setup", "quantity": "1", "unit_price": "1500.00"},
                        {"description": "Google Analytics Config", "quantity": "1", "unit_price": "350.00"}]),
            dict(client=c[3], num="INV-013", issue=d(-3),  due=d(17), status="sent",
                 items=[{"description": "E-commerce Integration", "quantity": "1", "unit_price": "3800.00"}]),
            dict(client=c[6], num="INV-014", issue=d(-7),  due=d(20), status="viewed",
                 items=[{"description": "Product Demo Video", "quantity": "1", "unit_price": "4200.00"},
                        {"description": "Subtitle Package", "quantity": "1", "unit_price": "300.00"}]),
            dict(client=c[2], num="INV-015", issue=d(-2),  due=d(22), status="sent",
                 items=[{"description": "Influencer Brief (x3)", "quantity": "3", "unit_price": "700.00"}]),
            dict(client=c[4], num="INV-016", issue=d(-1),  due=d(25), status="sent",
                 items=[{"description": "Instagram Content (Month 2)", "quantity": "1", "unit_price": "1800.00"},
                        {"description": "Story Templates", "quantity": "10", "unit_price": "80.00"}]),
            dict(client=c[8], num="INV-017", issue=d(-4),  due=d(30), status="viewed",
                 items=[{"description": "NDAs — batch of 5", "quantity": "5", "unit_price": "250.00"},
                        {"description": "Employment Contract Template", "quantity": "1", "unit_price": "800.00"}]),
            dict(client=c[5], num="INV-018", issue=d(0),   due=d(35), status="sent",
                 items=[{"description": "Annual Maintenance Contract", "quantity": "1", "unit_price": "5500.00"}]),
            dict(client=c[9], num="INV-019", issue=d(-1),  due=d(40), status="sent",
                 items=[{"description": "Email Newsletter Series (x6)", "quantity": "6", "unit_price": "420.00"},
                        {"description": "Copyediting Pass", "quantity": "1", "unit_price": "550.00"}]),
            dict(client=c[7], num="INV-020", issue=d(0),   due=d(45), status="sent",
                 items=[{"description": "3D Render Package", "quantity": "4", "unit_price": "1800.00"}]),
            dict(client=c[0], num="INV-021", issue=d(0),   due=d(50), status="sent",
                 items=[{"description": "Brand Campaign — Q3", "quantity": "1", "unit_price": "7200.00"}]),
            dict(client=c[1], num="INV-022", issue=d(0),   due=d(55), status="sent",
                 items=[{"description": "Monthly Retainer — May", "quantity": "1", "unit_price": "2500.00"}]),
            dict(client=c[3], num="INV-023", issue=d(0),   due=d(60), status="sent",
                 items=[{"description": "Web App Phase 2", "quantity": "1", "unit_price": "9500.00"}]),
            dict(client=c[6], num="INV-024", issue=d(0),   due=d(65), status="sent",
                 items=[{"description": "Explainer Video", "quantity": "1", "unit_price": "6000.00"},
                        {"description": "Voice-over", "quantity": "1", "unit_price": "800.00"}]),
            dict(client=c[4], num="INV-025", issue=d(0),   due=d(70), status="sent",
                 items=[{"description": "Paid Social Strategy", "quantity": "1", "unit_price": "2200.00"},
                        {"description": "Creative Brief", "quantity": "1", "unit_price": "600.00"}]),
            dict(client=c[2], num="INV-026", issue=d(0),   due=d(75), status="sent",
                 items=[{"description": "Campaign Analytics Report", "quantity": "1", "unit_price": "900.00"}]),
            dict(client=c[8], num="INV-027", issue=d(0),   due=d(80), status="sent",
                 items=[{"description": "IP Registration Filing", "quantity": "1", "unit_price": "1400.00"},
                        {"description": "Legal Research", "quantity": "3", "unit_price": "350.00"}]),
            dict(client=c[5], num="INV-028", issue=d(0),   due=d(85), status="sent",
                 items=[{"description": "Skylight Installation", "quantity": "2", "unit_price": "3200.00"}]),
            dict(client=c[9], num="INV-029", issue=d(0),   due=d(88), status="sent",
                 items=[{"description": "Brand Voice Guide", "quantity": "1", "unit_price": "1600.00"}]),

            # ---- DRAFT ----
            dict(client=c[7], num="INV-030", issue=d(0), due=d(30), status="draft",
                 items=[{"description": "Interior Renders — Phase 2", "quantity": "6", "unit_price": "1200.00"}]),
            dict(client=c[10 % 10], num="INV-031", issue=d(0), due=d(45), status="draft",
                 items=[{"description": "Logo Animation", "quantity": "1", "unit_price": "1800.00"}]),
        ]

        # Build Invoice ORM objects
        invoice_objs = []
        for row in invoices_data:
            inv = Invoice(
                client_id=row["client"].id,
                invoice_number=row["num"],
                issue_date=row["issue"],
                due_date=row["due"],
                status=row["status"],
                line_items=row["items"],
            )
            db.add(inv)
            invoice_objs.append((inv, row))

        db.flush()

        # ------------------------------------------------------------------
        # Payments for paid invoices (so "paid this month" stat is non-zero)
        # ------------------------------------------------------------------
        paid_days_ago = [0, 1, 1, 2, 0]  # one per paid invoice, all within this month
        for i, (inv, row) in enumerate(invoice_objs):
            if row["status"] != "paid":
                continue
            total = sum(
                Decimal(str(item["quantity"])) * Decimal(str(item["unit_price"]))
                for item in row["items"]
            )
            payment = Payment(
                invoice_id=inv.id,
                amount=total,
                stripe_payment_intent_id=f"pi_seed_{inv.invoice_number.lower().replace('-', '_')}",
                paid_at=paid_at(paid_days_ago[i % len(paid_days_ago)]),
            )
            db.add(payment)

        # ------------------------------------------------------------------
        # EmailLogs for overdue invoices (show follow-up history in detail view)
        # ------------------------------------------------------------------
        for inv, row in invoice_objs:
            if row["status"] != "overdue":
                continue
            total = sum(
                Decimal(str(item["quantity"])) * Decimal(str(item["unit_price"]))
                for item in row["items"]
            )
            logs = [
                EmailLog(
                    invoice_id=inv.id,
                    sent_at=datetime.utcnow() - timedelta(days=20),
                    subject=f"Invoice {inv.invoice_number} — Payment Due",
                    body=f"Hi {row['client'].name}, please find your invoice for ${total} attached.",
                    follow_up_day=0,
                ),
                EmailLog(
                    invoice_id=inv.id,
                    sent_at=datetime.utcnow() - timedelta(days=17),
                    subject=f"Friendly reminder — {inv.invoice_number}",
                    body=f"Hi {row['client'].name}, just a quick reminder that invoice {inv.invoice_number} for ${total} is now 3 days overdue.",
                    follow_up_day=3,
                ),
            ]
            db.add_all(logs)

        db.commit()
        inv_count = len(invoice_objs)
        print(f"Seeded {len(clients)} clients, {inv_count} invoices, payments, and email logs.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
