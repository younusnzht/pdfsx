import uuid

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class MLTrainingSample(UUIDPKMixin, TimestampMixin, Base):
    """
    Every human correction made in the review UI lands here as a labeled
    example. This is the improvement loop that substitutes for an LLM API:
    periodically retrain the classical models (institution classifier,
    debit/credit classifier, CRF field-tagger) on the growing corpus
    instead of calling out to a generative model at inference time.

    Deliberately NOT tenant-scoped on read — training pools corrections
    across tenants to improve the shared model. Strip anything
    tenant-identifying before it lands here (see services/ml/README).
    """

    __tablename__ = "ml_training_samples"

    source_transaction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("transactions.id"))
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "debit_credit" | "field_tagging" | "template"
    input_features: Mapped[dict] = mapped_column(JSON, nullable=False)
    corrected_label: Mapped[dict] = mapped_column(JSON, nullable=False)
    used_in_training_run: Mapped[str | None] = mapped_column(String(50), nullable=True)
