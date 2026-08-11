import uuid

from pydantic import BaseModel, ConfigDict


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    raw_date: str
    raw_description: str
    raw_debit: str | None
    raw_credit: str | None
    confidence: float
    is_uncertain: bool
    reviewed: bool
    row_order: int


class TransactionCorrection(BaseModel):
    """Sent from the review UI when a user edits a row. Persisting this
    also writes an MLTrainingSample for the active-learning loop."""

    raw_date: str | None = None
    raw_description: str | None = None
    raw_debit: str | None = None
    raw_credit: str | None = None
