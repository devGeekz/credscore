import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.rate_limiter import limiter
from app.middleware.tenant import get_current_user
from app.models import Tenant, User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.schemas.report import ApiKeyCreated, ApiKeyOut
from app.utils.security import create_access_token, hash_password, verify_password

router = APIRouter()

db_dependency = Depends(get_db)
current_user_dependency = Depends(get_current_user)

API_KEY_PREFIX = "cs_live_"


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
def register(payload: RegisterRequest, db: Session = db_dependency):
    existing = db.query(User).filter(User.email == payload.admin_email).first()
    if existing:
        raise HTTPException(
            status_code=400, detail="A user with this email already exists"
        )

    tenant = Tenant(
        name=payload.tenant_name,
        org_type=payload.org_type,
        contact_email=payload.contact_email,
        subscription_plan="pilot",
        subscription_status="trial",
    )
    db.add(tenant)
    db.flush()

    user = User(
        tenant_id=tenant.id,
        email=payload.admin_email,
        name=payload.admin_name,
        role="admin",
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(
        {"sub": str(user.id), "tenant_id": str(tenant.id), "role": user.role}
    )
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest, db: Session = db_dependency):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_access_token(
        {"sub": str(user.id), "tenant_id": str(user.tenant_id), "role": user.role}
    )
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


def _masked(stored: str) -> str:
    return stored.split(":", 1)[0] + "\u2026"


@router.post(
    "/api-keys", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED
)
def create_api_key(
    current_user: User = Depends(get_current_user),
    db: Session = db_dependency,
):
    """One key per tenant (matches the single tenants.api_key_hash column).
    The plaintext key is returned once; only a prefix + SHA-256 is stored."""
    key = API_KEY_PREFIX + secrets.token_urlsafe(24)
    tenant = db.get(Tenant, current_user.tenant_id)
    tenant.api_key_hash = f"{key[:15]}:{hashlib.sha256(key.encode()).hexdigest()}"
    db.commit()
    return ApiKeyCreated(api_key=key, masked=_masked(tenant.api_key_hash), active=True)


@router.get("/api-keys", response_model=ApiKeyOut)
def get_api_key(
    current_user: User = Depends(get_current_user),
    db: Session = db_dependency,
):
    tenant = db.get(Tenant, current_user.tenant_id)
    if not tenant.api_key_hash:
        return ApiKeyOut(masked=None, active=False)
    return ApiKeyOut(masked=_masked(tenant.api_key_hash), active=True)


@router.delete("/api-keys", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    current_user: User = Depends(get_current_user),
    db: Session = db_dependency,
):
    tenant = db.get(Tenant, current_user.tenant_id)
    tenant.api_key_hash = None
    db.commit()
