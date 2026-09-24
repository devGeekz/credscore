from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Merchant, Statement
from app.services.consent_service import generate_and_store_otp, is_duplicate_message, verify_otp
from app.services.storage_service import upload_statement_file
from app.services.whatsapp_service import InboundMessage, download_media, parse_webhook_payload, send_text_message
from app.workers.parse_tasks import parse_statement_task

router = APIRouter()


@router.get("")
def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return Response(content=hub_challenge, media_type="text/plain")
    return Response(status_code=403)


@router.post("")
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    messages = parse_webhook_payload(payload)

    for msg in messages:
        if is_duplicate_message(msg.wamid):
            continue

        merchant = (
            db.query(Merchant)
            .filter(Merchant.phone == msg.from_phone)
            .order_by(Merchant.created_at.desc())
            .first()
        )

        if merchant is None:
            send_text_message(
                msg.from_phone,
                "We don't recognize this number yet. Ask your lender to add you as an applicant first.",
            )
            continue

        if not merchant.consent_verified:
            _handle_consent_flow(msg, merchant, db)
            continue

        if msg.msg_type == "document" and msg.media_id:
            _handle_statement_upload(msg, merchant, db)
        else:
            send_text_message(msg.from_phone, "Please send your MoMo statement as a PDF or CSV document.")

    return {"status": "received"}


def _handle_consent_flow(msg: InboundMessage, merchant: Merchant, db: Session) -> None:
    if msg.msg_type == "text" and msg.text and msg.text.strip().isdigit():
        if verify_otp(msg.from_phone, msg.text.strip()):
            merchant.consent_verified = True
            merchant.consent_timestamp = datetime.now(timezone.utc)
            db.commit()
            send_text_message(
                msg.from_phone,
                "Thanks — consent confirmed. Please send your MoMo statement as a PDF or CSV.",
            )
        else:
            send_text_message(
                msg.from_phone, "That code didn't match or has expired. Reply anything to get a new one."
            )
        return

    code = generate_and_store_otp(msg.from_phone)
    send_text_message(
        msg.from_phone,
        f"To let your lender access your MoMo statement, reply with this code: {code} (valid 10 minutes).",
    )


def _handle_statement_upload(msg: InboundMessage, merchant: Merchant, db: Session) -> None:
    file_bytes, _mime_type = download_media(msg.media_id)
    object_key = upload_statement_file(file_bytes, msg.media_filename or "statement", str(merchant.tenant_id))

    statement = Statement(
        merchant_id=merchant.id,
        source_channel="whatsapp",
        file_url=object_key,
        parse_status="pending",
    )
    db.add(statement)
    db.commit()
    db.refresh(statement)

    parse_statement_task.delay(str(statement.id))

    send_text_message(msg.from_phone, "Got it — your statement is being processed.")