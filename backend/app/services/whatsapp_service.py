"""
Thin wrapper around Meta's WhatsApp Cloud API.
Docs: https://developers.facebook.com/docs/whatsapp/cloud-api
"""

from dataclasses import dataclass
from typing import Optional

import httpx

from app.config import settings

GRAPH_API_VERSION = "v21.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


@dataclass
class InboundMessage:
    wamid: str  # WhatsApp message id — the idempotency key for webhook retries
    from_phone: str
    msg_type: str  # "text" | "document" | "image" | ...
    text: Optional[str] = None
    media_id: Optional[str] = None
    media_filename: Optional[str] = None
    media_mime_type: Optional[str] = None


def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.whatsapp_api_token}"}


def send_text_message(to_phone: str, body: str) -> None:
    url = f"{GRAPH_API_BASE}/{settings.whatsapp_phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": body},
    }
    response = httpx.post(url, headers=_headers(), json=payload, timeout=10)
    response.raise_for_status()


def download_media(media_id: str) -> tuple[bytes, str]:
    """Two-step per Meta's API: resolve the media id to a temp URL, then fetch it."""
    meta_url = f"{GRAPH_API_BASE}/{media_id}"
    meta_response = httpx.get(meta_url, headers=_headers(), timeout=10)
    meta_response.raise_for_status()
    meta = meta_response.json()

    file_response = httpx.get(meta["url"], headers=_headers(), timeout=30)
    file_response.raise_for_status()
    return file_response.content, meta.get("mime_type", "application/octet-stream")


def parse_webhook_payload(payload: dict) -> list[InboundMessage]:
    messages: list[InboundMessage] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                msg_type = msg.get("type")
                inbound = InboundMessage(wamid=msg["id"], from_phone=msg["from"], msg_type=msg_type)
                if msg_type == "text":
                    inbound.text = msg.get("text", {}).get("body")
                elif msg_type in ("document", "image"):
                    media = msg.get(msg_type, {})
                    inbound.media_id = media.get("id")
                    inbound.media_filename = media.get("filename")
                    inbound.media_mime_type = media.get("mime_type")
                messages.append(inbound)
    return messages