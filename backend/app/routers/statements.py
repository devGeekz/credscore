import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request, UploadFile, File
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.rate_limiter import limiter
from app.middleware.tenant import get_current_user
from app.models import Merchant, Statement, User
from app.schemas.statement import StatementOut
from app.services.storage_service import (
    LOCAL_STORAGE_DIR,
    generate_download_url,
    s3_configured,
    upload_statement_file,
)
from app.utils.errors import AppError, NotFoundError
from app.workers.parse_tasks import queue_parse

router = APIRouter()

ALLOWED_CONTENT_TYPES = {"application/pdf", "text/csv", "application/vnd.ms-excel"}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15MB


@router.post("/upload", response_model=StatementOut, status_code=201)
@limiter.limit("20/minute")
async def upload_statement(
    request: Request,
    merchant_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
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

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise AppError("Unsupported file type — upload a PDF or CSV", status_code=400, code="unsupported_file_type")

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise AppError("File too large (max 15MB)", status_code=400, code="file_too_large")

    object_key = upload_statement_file(contents, file.filename or "statement", str(current_user.tenant_id))

    statement = Statement(
        merchant_id=merchant.id,
        source_channel="web_upload",
        file_url=object_key,
        parse_status="pending",
    )
    db.add(statement)
    db.commit()
    queue_parse(statement.id)
    db.refresh(statement)  # the inline (dev) parse may have finished already

    return statement


@router.get("", response_model=list[StatementOut])
def list_statements(
    merchant_id: uuid.UUID | None = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Statement)
        .join(Merchant)
        .filter(Merchant.tenant_id == current_user.tenant_id)
        .order_by(Statement.created_at.desc())
    )
    if merchant_id is not None:
        query = query.filter(Statement.merchant_id == merchant_id)
    return query.limit(limit).all()


@router.get("/{statement_id}", response_model=StatementOut)
def get_statement(
    statement_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    statement = (
        db.query(Statement)
        .join(Merchant)
        .filter(Statement.id == statement_id, Merchant.tenant_id == current_user.tenant_id)
        .first()
    )
    if statement is None:
        raise NotFoundError("Statement not found")
    return statement


@router.post("/{statement_id}/requeue", response_model=StatementOut, status_code=202)
def requeue_statement(
    statement_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    statement = (
        db.query(Statement)
        .join(Merchant)
        .filter(Statement.id == statement_id, Merchant.tenant_id == current_user.tenant_id)
        .first()
    )
    if statement is None:
        raise NotFoundError("Statement not found")
    if statement.parse_status == "parsed":
        raise AppError("Statement already parsed", status_code=409, code="already_parsed")

    statement.parse_status = "pending"
    statement.parse_error = None
    db.commit()
    queue_parse(statement.id)
    db.refresh(statement)  # the inline (dev) parse may have finished already
    return statement


@router.get("/{statement_id}/download")
def download_statement(
    statement_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """s3: short-lived presigned redirect; dev: the local file itself."""
    statement = (
        db.query(Statement)
        .join(Merchant)
        .filter(Statement.id == statement_id, Merchant.tenant_id == current_user.tenant_id)
        .first()
    )
    if statement is None:
        raise NotFoundError("Statement not found")

    if s3_configured():
        return RedirectResponse(generate_download_url(statement.file_url))
    return FileResponse(
        LOCAL_STORAGE_DIR / statement.file_url,
        filename=Path(statement.file_url).name,
    )