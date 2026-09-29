"""Tenant webhook configuration (Phase 5: outbound score webhooks)."""

import sqlalchemy as sa
from alembic import op

revision = "c7e1f0a93b42"
down_revision = "a0eacbbcb4ed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("webhook_url", sa.String(), nullable=True))
    op.add_column("tenants", sa.Column("webhook_secret", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "webhook_secret")
    op.drop_column("tenants", "webhook_url")
