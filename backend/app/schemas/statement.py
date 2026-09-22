import uuid
from datetime import datetime

from pydantic import BaseModel


class StatementOut(BaseModel):
    id: uuid.UUID
    merchant_id: uuid.UUID
    source_channel: str
    parse_status: str
    created_at: datetime

    class Config:
        from_attributes = True