import enum

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class SubscriptionTier(str, enum.Enum):
    trial = "trial"
    starter = "starter"
    pro = "pro"
    enterprise = "enterprise"


class Tenant(UUIDPKMixin, TimestampMixin, Base):
    """A paying business/accountant account. Every tenant-scoped table
    carries a tenant_id FK back to this table."""

    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier), default=SubscriptionTier.trial, nullable=False
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
