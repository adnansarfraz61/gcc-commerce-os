"""Create Amazon seller authorizations.

Revision ID: 0002_create_amazon_seller_authorizations
Revises: 0001_initial_platform_tables
Create Date: 2026-05-15 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_create_amazon_seller_authorizations"
down_revision: str | None = "0001_initial_platform_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "amazon_seller_authorizations",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("seller_id", sa.String(length=255), nullable=False),
        sa.Column("marketplace_id", sa.String(length=64), nullable=False),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_amazon_seller_authorizations_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_amazon_seller_authorizations")),
        sa.UniqueConstraint(
            "tenant_id",
            "seller_id",
            "marketplace_id",
            name="uq_amazon_seller_authorizations_tenant_seller_marketplace",
        ),
    )
    op.create_index(
        "ix_amazon_seller_authorizations_marketplace_id",
        "amazon_seller_authorizations",
        ["marketplace_id"],
        unique=False,
    )
    op.create_index(
        "ix_amazon_seller_authorizations_seller_id",
        "amazon_seller_authorizations",
        ["seller_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_amazon_seller_authorizations_tenant_id"),
        "amazon_seller_authorizations",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_amazon_seller_authorizations_tenant_id"),
        table_name="amazon_seller_authorizations",
    )
    op.drop_index(
        "ix_amazon_seller_authorizations_seller_id",
        table_name="amazon_seller_authorizations",
    )
    op.drop_index(
        "ix_amazon_seller_authorizations_marketplace_id",
        table_name="amazon_seller_authorizations",
    )
    op.drop_table("amazon_seller_authorizations")
