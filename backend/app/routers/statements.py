import uuid

from fastapi import APIRouter, Depends, Form, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.tenant import get_current_user
from app.models import Merchant, Statement, User
from app.schemas.statement import StatementOut
from app.services.storage_service import upload_statement_file
from app.utils.errors import AppError, NotFoundError
from app.workers.parse_tasks import parse_statement_task

router = APIRouter()

ALLOWED_CONTENT_TYPES = {"application/pdf", "text/csv", "application/vnd.ms-excel"}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15MB


@router.post("/upload", response_model=StatementOut, status_code=201)
async def upload_statement(
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
    db.refresh(statement)
    parse_statement_task.delay(str(statement.id))

    # Phase 3 hooks in here: queue a Celery parse_task for this statement.id

    return statement


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