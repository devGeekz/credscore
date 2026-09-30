from typing import Any

from pydantic import BaseModel, ConfigDict


class WhatsAppWebhookIn(BaseModel):
    """minimal shape of a meta webhook — extra fields are ignored, a body
    that is not a json object is rejected with 422 instead of a 500."""

    model_config = ConfigDict(extra="ignore")

    object: str = ""
    entry: list[dict[str, Any]] = []
    statuses: list[dict[str, Any]] = []
