import uuid

from pydantic import BaseModel, ConfigDict


class StatementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    institution: str | None
    status: str
    page_count: int | None
    error_message: str | None
