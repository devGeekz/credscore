import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.middleware.rate_limiter import limiter
from app.middleware.tenant import get_current_user, require_admin
from app.models import AuthToken, Tenant, User
from app.schemas.auth import (
    CreateUserRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserOut,
)
from app.schemas.report import ApiKeyCreated, ApiKeyOut
from app.utils.errors import ConflictError, UnauthorizedError
from app.utils.mailer import send_password_reset_email
from app.utils.security import _parse_expires_in, create_access_token, hash_password, verify_password

router = APIRouter()

db_dependency = Depends(get_db)
current_user_dependency = Depends(get_current_user)

API_KEY_PREFIX = "cs_live_"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _issue_tokens(db: Session, user: User) -> TokenResponse:
    """access + rotated refresh: only the refresh hash is stored."""
    access = create_access_token(
        {"sub": str(user.id), "tenant_id": str(user.tenant_id), "role": user.role}
    )
    refresh = secrets.token_urlsafe(32)
    db.add(AuthToken(
        user_id=user.id,
        token_hash=_hash_token(refresh),
        purpose="refresh",
        expires_at=datetime.utcnow() + _parse_expires_in(settings.refresh_expires_in),
    ))
    db.commit()
    return TokenResponse(access_token=access, refresh_token=refresh, user=UserOut.model_validate(user))


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

    return _issue_tokens(db, user)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest, db: Session = db_dependency):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    return _issue_tokens(db, user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = db_dependency):
    """rotation: the used refresh token is revoked and a new pair is issued."""
    row = db.query(AuthToken).filter(
        AuthToken.token_hash == _hash_token(payload.refresh_token),
        AuthToken.purpose == "refresh",
        AuthToken.revoked_at.is_(None),
    ).first()
    if row is None or row.expires_at < datetime.utcnow():
        raise UnauthorizedError("Invalid or expired refresh token")

    user = db.get(User, row.user_id)
    row.revoked_at = datetime.utcnow()
    if user is None or not user.is_active:
        db.commit()
        raise UnauthorizedError("Invalid or expired refresh token")
    return _issue_tokens(db, user)  # also commits the revocation


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: LogoutRequest, db: Session = db_dependency):
    row = db.query(AuthToken).filter(
        AuthToken.token_hash == _hash_token(payload.refresh_token),
        AuthToken.purpose == "refresh",
    ).first()
    if row and row.revoked_at is None:
        row.revoked_at = datetime.utcnow()
        db.commit()


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
def forgot_password(request: Request, payload: ForgotPasswordRequest, db: Session = db_dependency):
    """always 200 so the endpoint can't be used to enumerate accounts."""
    user = db.query(User).filter(User.email == payload.email).first()
    if user:
        token = secrets.token_urlsafe(32)
        db.add(AuthToken(
            user_id=user.id,
            token_hash=_hash_token(token),
            purpose="password_reset",
            expires_at=datetime.utcnow() + timedelta(hours=1),
        ))
        db.commit()
        link = f"{settings.web_url}/reset-password?token={token}"
        send_password_reset_email(user.email, link)
    return {"status": "ok"}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(payload: ResetPasswordRequest, db: Session = db_dependency):
    row = db.query(AuthToken).filter(
        AuthToken.token_hash == _hash_token(payload.token),
        AuthToken.purpose == "password_reset",
        AuthToken.revoked_at.is_(None),
    ).first()
    if row is None or row.expires_at < datetime.utcnow():
        raise UnauthorizedError("Invalid or expired reset token")

    user = db.get(User, row.user_id)
    row.revoked_at = datetime.utcnow()
    if user is None:
        db.commit()
        raise UnauthorizedError("Invalid or expired reset token")

    user.password_hash = hash_password(payload.new_password)
    # a reset kills every active session for that account
    db.query(AuthToken).filter(
        AuthToken.user_id == user.id,
        AuthToken.purpose == "refresh",
        AuthToken.revoked_at.is_(None),
    ).update({"revoked_at": datetime.utcnow()})
    db.commit()
    return {"status": "ok"}


@router.get("/users", response_model=list[UserOut])
def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = db_dependency,
):
    return (
        db.query(User)
        .filter(User.tenant_id == current_user.tenant_id)
        .order_by(User.created_at)
        .all()
    )


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: CreateUserRequest,
    current_user: User = Depends(require_admin),
    db: Session = db_dependency,
):
    """admins add teammates to their own tenant only."""
    if db.query(User).filter(User.email == payload.email).first():
        raise ConflictError("A user with this email already exists")
    user = User(
        tenant_id=current_user.tenant_id,
        email=payload.email,
        name=payload.name,
        role=payload.role,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _masked(stored: str) -> str:
    return stored.split(":", 1)[0] + "\u2026"


@router.post(
    "/api-keys", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED
)
def create_api_key(
    current_user: User = Depends(require_admin),
    db: Session = db_dependency,
):
    """one key per tenant (matches the single tenants.api_key_hash column).
    the plaintext key is returned once; only a prefix + sha-256 is stored."""
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
    current_user: User = Depends(require_admin),
    db: Session = db_dependency,
):
    tenant = db.get(Tenant, current_user.tenant_id)
    tenant.api_key_hash = None
    db.commit()
