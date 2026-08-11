import enum
import uuid

from sqlalchemy import Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantScopedMixin, TimestampMixin, UUIDPKMixin


class StatementStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    needs_review = "needs_review"
    reviewed = "reviewed"
    failed = "failed"


class SourceType(str, enum.Enum):
    text_pdf = "text_pdf"       # extractable text layer — deterministic path
    scanned_pdf = "scanned_pdf"  # image-only — OCR path
    image = "image"              # standalone screenshot/photo — OCR path


class Statement(UUIDPKMixin, TimestampMixin, TenantScopedMixin, Base):
    __tablename__ = "statements"

    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)  # local disk path
    source_type: Mapped[SourceType | None] = mapped_column(Enum(SourceType), nullable=True)
    institution: Mapped[str | None] = mapped_column(String(255), nullable=True)  # detected e.g. "RBC", "Amex"
    institution_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[StatementStatus] = mapped_column(
        Enum(StatementStatus), default=StatementStatus.uploaded, nullable=False
    )
    page_count: Mapped[int | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
