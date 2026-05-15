import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Marketplace(str, enum.Enum):
    AMAZON = "amazon"
    NOON = "noon"
    SHOPIFY = "shopify"
    TIKTOK_SHOP = "tiktok_shop"


class AuthorizationStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ERROR = "error"


class SellerAuthorization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "seller_authorizations"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "marketplace",
            "external_seller_id",
            name="uq_seller_authorizations_tenant_marketplace_seller",
        ),
        Index("ix_seller_authorizations_marketplace_status", "marketplace", "status"),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    marketplace: Mapped[str] = mapped_column(String(40), nullable=False)
    external_seller_id: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=AuthorizationStatus.ACTIVE.value,
    )
    encrypted_refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    access_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scopes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    marketplace_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tenant = relationship("Tenant", back_populates="seller_authorizations")


class AmazonSellerAuthorization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "amazon_seller_authorizations"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "seller_id",
            "marketplace_id",
            name="uq_amazon_seller_authorizations_tenant_seller_marketplace",
        ),
        Index("ix_amazon_seller_authorizations_seller_id", "seller_id"),
        Index("ix_amazon_seller_authorizations_marketplace_id", "marketplace_id"),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seller_id: Mapped[str] = mapped_column(String(255), nullable=False)
    marketplace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    encrypted_refresh_token: Mapped[str] = mapped_column(Text, nullable=False)

    tenant = relationship("Tenant", back_populates="amazon_seller_authorizations")
