"""Run from the backend directory with: python seed.py"""

from datetime import date, timedelta

from database import Base, SessionLocal, engine
from models import Client, Invoice

Base.metadata.create_all(bind=engine)


def main() -> None:
    db = SessionLocal()
    try:
        if db.query(Client).count() > 0:
            print("Seed data already exists. Skipping.")
            return

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
                client_id=clients[0].id,
                invoice_number="INV-001",
                issue_date=today - timedelta(days=30),
                due_date=today - timedelta(days=10),
                status="overdue",
                line_items=[
                    {"description": "Brand Strategy", "quantity": "1", "unit_price": "2500.00"},
                    {"description": "Logo Design", "quantity": "1", "unit_price": "750.00"},
                ],
            ),
            Invoice(
                client_id=clients[1].id,
                invoice_number="INV-002",
                issue_date=today - timedelta(days=10),
                due_date=today + timedelta(days=20),
                status="sent",
                line_items=[
                    {"description": "Consulting Hours", "quantity": "8", "unit_price": "150.00"}
                ],
            ),
            Invoice(
                client_id=clients[2].id,
                invoice_number="INV-003",
                issue_date=today,
                due_date=today + timedelta(days=30),
                status="draft",
                line_items=[
                    {"description": "Website Copy", "quantity": "3", "unit_price": "400.00"}
                ],
            ),
        ]
        db.add_all(invoices)
        db.commit()
        print("Seeded 3 clients and 3 invoices.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
