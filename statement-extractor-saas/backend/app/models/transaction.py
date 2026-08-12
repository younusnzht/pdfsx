import uuid

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantScopedMixin, TimestampMixin, UUIDPKMixin


class Transaction(UUIDPKMixin, TimestampMixin, TenantScopedMixin, Base):
    """
    One extracted row. Debit/credit amounts are stored as separate nullable
    columns (never both populated) mirroring the skill's output contract —
    never re-derive one from the other, never store a placeholder in the
    empty column.

    raw_date / raw_description / raw_amount preserve exactly what was on the
    statement (see NON-NEGOTIABLE ACCURACY rules). Numeric parsed fields are
    kept alongside for querying/reporting, but the raw fields are the
    source of truth for anything reconciliation-related.
    """

    __tablename__ = "transactions"

    statement_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("statements.id"), index=True)

    raw_date: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_description: Mapped[str] = mapped_column(String(2000), nullable=False)
    raw_debit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    raw_credit: Mapped[str | None] = mapped_column(String(50), nullable=True)

    parsed_date: Mapped[str | None] = mapped_column(String(20), nullable=True)  # ISO, populated on review
    debit_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    credit_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)

    confidence: Mapped[float] = mapped_column(default=1.0, nullable=False)
    is_uncertain: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    row_order: Mapped[int] = mapped_column(nullable=False)  # preserves source order

    reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    was_corrected: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="True if a human changed any field — feeds ml_training_samples"
    )
