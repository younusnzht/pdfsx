import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantScopedMixin, TimestampMixin, UUIDPKMixin


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class ExtractionJob(UUIDPKMixin, TimestampMixin, TenantScopedMixin, Base):
    """Tracks a single Celery task processing one statement, so the API can
    report progress without polling Celery directly."""

    __tablename__ = "extraction_jobs"

    statement_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("statements.id"), index=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.queued, nullable=False)
    current_step: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g. "ocr", "classify", "extract"
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
