import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UUIDPKMixin:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TenantScopedMixin:
    """
    Every tenant-owned table gets a tenant_id column. This alone is NOT
    sufficient isolation — pair it with a PostgreSQL Row-Level Security (RLS)
    policy (see backend/alembic/versions for the RLS migration) so a bug in
    application-layer filtering can't leak one tenant's financial data to
    another. Never trust tenant_id filtering in Python code alone for a
    product handling bank statements.
    """

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
