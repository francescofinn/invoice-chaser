from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import Client, Invoice
from sqlalchemy.orm import joinedload
from schemas import ClientCreate, ClientResponse, ClientUpdate, ClientWithInvoices

router = APIRouter()


def _get_client_or_404(db: Session, client_id: int) -> Client:
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


@router.get("", response_model=list[ClientResponse])
def list_clients(db: Session = Depends(get_db)):
    return db.scalars(select(Client).order_by(Client.id)).all()


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(payload: ClientCreate, db: Session = Depends(get_db)):
    client = Client(**payload.model_dump())
    db.add(client)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Client already exists") from exc
    db.refresh(client)
    return client


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: int, db: Session = Depends(get_db)):
    return _get_client_or_404(db, client_id)


@router.get("/{client_id}/profile", response_model=ClientWithInvoices)
def get_client_profile(client_id: int, db: Session = Depends(get_db)):
    client = db.scalars(
        select(Client)
        .options(joinedload(Client.invoices).joinedload(Invoice.client))
        .where(Client.id == client_id)
    ).unique().one_or_none()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


@router.put("/{client_id}", response_model=ClientResponse)
def update_client(client_id: int, payload: ClientUpdate, db: Session = Depends(get_db)):
    client = _get_client_or_404(db, client_id)
    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(client, field_name, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Client already exists") from exc
    db.refresh(client)
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(client_id: int, db: Session = Depends(get_db)):
    client = _get_client_or_404(db, client_id)
    has_invoices = db.scalar(select(Invoice.id).where(Invoice.client_id == client_id).limit(1))
    if has_invoices:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a client with associated invoices",
        )

    db.delete(client)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
