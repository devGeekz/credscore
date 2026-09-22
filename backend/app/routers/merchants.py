import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.tenant import get_current_user
from app.models import Merchant, User
from app.schemas.merchant import MerchantCreate, MerchantOut
from app.utils.errors import NotFoundError

router = APIRouter()


@router.post("", response_model=MerchantOut, status_code=201)
def create_merchant(
    payload: MerchantCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    merchant = Merchant(tenant_id=current_user.tenant_id, **payload.model_dump())
    db.add(merchant)
    db.commit()
    db.refresh(merchant)
    return merchant


@router.get("", response_model=list[MerchantOut])
def list_merchants(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Merchant)
        .filter(Merchant.tenant_id == current_user.tenant_id)
        .order_by(Merchant.created_at.desc())
        .all()
    )


@router.get("/{merchant_id}", response_model=MerchantOut)
def get_merchant(
    merchant_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    merchant = (
        db.query(Merchant)
        .filter(Merchant.id == merchant_id, Merchant.tenant_id == current_user.tenant_id)
        .first()
    )
    if merchant is None:
        raise NotFoundError("Merchant not found")
    return merchant